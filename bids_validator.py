import os
import re
import logging
import json
import sys
from jsonschema import validate, ValidationError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BIDSValidator:
    def __init__(self, root_path):
        self.root_path = root_path
        self.missing_files = []
        self.unexpected_files = []
        self.invalid_json_files = []
        self.required_root_files = {
            "dataset_description.json": False,
            "CITATION.cff": True,
            "CHANGES": True,
            "LICENSE": True,
            "participants.tsv": False,
            "participants.json": False,
            "README": False
        }
        self.sub_dir_prefix = "sub-"
        self.ses_dir_prefix = "ses-"
        self.allowed_session_subdirs = [
            "func", "dwi", "fmap", "anat", "perf", "meg", "eeg",
            "ieeg", "beh", "pet", "micr", "nirs", "motion"
        ]
        self.schemas = {}
        self.load_schemas()

    def load_schemas(self):
        schema_dir = 'schemas'
        schema_files = {
            'dataset_description.json': 'dataset_description_schema.json',
            'participants.json': 'participants_schema.json',
            'sub-xx_ses-xx_task-xx_beh.json': 'task_beh_schema.json',
            'sub-xx_ses-xx_task-xx_events.json': 'task_events_schema.json',
            'sub-xx_ses-xx_task-xx_recording-xx_physio.json': 'task_physio_schema.json'
        }
        for key, schema_file in schema_files.items():
            schema_path = os.path.join(schema_dir, schema_file)
            try:
                with open(schema_path) as f:
                    self.schemas[key] = json.load(f)
                logger.info(f"Schema {schema_file} loaded successfully")
            except FileNotFoundError:
                logger.warning(f"Schema file {schema_file} not found. Proceeding without schema for {key}")

    def validate_file_structure(self):
        logger.info("Starting validation")
        self.validate_root_files()
        self.validate_directories()
        self.validate_json_files()
        return self.report_results()

    def validate_root_files(self):
        root_files = {f.lower(): f for f in os.listdir(self.root_path) if os.path.isfile(os.path.join(self.root_path, f))}
        for file, optional in self.required_root_files.items():
            if file.lower() not in root_files and not optional:
                self.missing_files.append(file)
        
        for file in root_files.values():
            if file.lower() not in [key.lower() for key in self.required_root_files.keys()]:
                self.unexpected_files.append(file)

    def validate_directories(self):
        sub_dirs = []
        for d in os.listdir(self.root_path):
            dir_path = os.path.join(self.root_path, d)
            if os.path.isdir(dir_path):
                if d.lower().startswith(self.sub_dir_prefix):
                    sub_dirs.append(d)
                else:
                    self.unexpected_files.append(f"Non-sub directory '{d}' found in the root directory")

        if not sub_dirs:
            self.missing_files.append(f"No directories starting with '{self.sub_dir_prefix}' found")
        else:
            for sub_dir in sub_dirs:
                self.validate_sub_directory(sub_dir)

    def validate_sub_directory(self, sub_dir):
        sub_dir_path = os.path.join(self.root_path, sub_dir)
        for item in os.listdir(sub_dir_path):
            item_path = os.path.join(sub_dir_path, item)
            if os.path.isdir(item_path) and not item.lower().startswith(self.ses_dir_prefix):
                self.unexpected_files.append(f"Non-session directory '{item}' found in '{sub_dir}'")

        ses_dirs = [d for d in os.listdir(sub_dir_path) if os.path.isdir(os.path.join(sub_dir_path, d)) and d.lower().startswith(self.ses_dir_prefix)]
        if not ses_dirs:
            self.missing_files.append(f"No session directories starting with '{self.ses_dir_prefix}' found in '{sub_dir}'")
        else:
            for ses_dir in ses_dirs:
                self.validate_session_directory(sub_dir, ses_dir)

    def validate_session_directory(self, sub_dir, ses_dir):
        sub_label = sub_dir[len(self.sub_dir_prefix):]
        ses_label = ses_dir[len(self.ses_dir_prefix):]
        pattern = re.compile(rf"^sub-{sub_label}_ses-{ses_label}", re.IGNORECASE)
        ses_dir_path = os.path.join(self.root_path, sub_dir, ses_dir)
        session_subdirs = [d for d in os.listdir(ses_dir_path) if os.path.isdir(os.path.join(ses_dir_path, d)) and d.lower() in self.allowed_session_subdirs]
        if not session_subdirs:
            self.missing_files.append(f"No valid session subdirectories found in '{ses_dir}' of '{sub_dir}'")
        else:
            for session_subdir in session_subdirs:
                session_subdir_path = os.path.join(ses_dir_path, session_subdir)
                for file in os.listdir(session_subdir_path):
                    if os.path.isfile(os.path.join(session_subdir_path, file)):
                        if not pattern.match(file):
                            self.unexpected_files.append(f"File '{file}' in '{session_subdir_path}' does not start with 'sub-{sub_label}[_ses-{ses_label}]'")

    def validate_json_files(self):
        if not self.schemas:
            return
        
        # Function to get the schema key based on the filename pattern
        def get_schema_key(filename):
            if re.match(r'sub-\d+_ses-\d+_task-.*_beh\.json', filename):
                return 'sub-xx_ses-xx_task-xx_beh.json'
            elif re.match(r'sub-\d+_ses-\d+_task-.*_events\.json', filename):
                return 'sub-xx_ses-xx_task-xx_events.json'
            elif re.match(r'sub-\d+_ses-\d+_task-.*_recording-.*_physio\.json', filename):
                return 'sub-xx_ses-xx_task-xx_recording-xx_physio.json'
            else:
                return None

        # Validate root-level JSON files
        for json_file in ['dataset_description.json', 'participants.json']:
            json_path = os.path.join(self.root_path, json_file)
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    try:
                        data = json.load(f)
                        validate(instance=data, schema=self.schemas[json_file])
                        logger.info(f"{json_file} is valid according to the schema")
                    except ValidationError as e:
                        self.invalid_json_files.append(f"{json_file}: {str(e)}")
                    except json.JSONDecodeError:
                        self.invalid_json_files.append(f"{json_file}: invalid JSON")
        
        # Validate JSON files in subdirectories
        for subdir, dirs, files in os.walk(self.root_path):
            for file in files:
                if file.endswith(".json"):
                    json_path = os.path.join(subdir, file)
                    schema_key = get_schema_key(file)
                    if schema_key and schema_key in self.schemas:
                        with open(json_path, 'r') as f:
                            try:
                                data = json.load(f)
                                validate(instance=data, schema=self.schemas[schema_key])
                                logger.info(f"{file} is valid according to the schema")
                            except ValidationError as e:
                                self.invalid_json_files.append(f"{file}: {str(e)}")
                            except json.JSONDecodeError:
                                self.invalid_json_files.append(f"{file}: invalid JSON")

    def report_results(self):
        if self.missing_files or self.unexpected_files or self.invalid_json_files:
            if self.missing_files:
                logger.warning("Validation failed. Missing files/directories:")
                for item in self.missing_files:
                    logger.warning(f"- {item}")
            if self.unexpected_files:
                logger.warning("Unexpected files/directories found:")
                for item in self.unexpected_files:
                    logger.warning(f"- {item}")
            if self.invalid_json_files:
                logger.warning("Invalid JSON files:")
                for item in self.invalid_json_files:
                    logger.warning(f"- {item}")
            return False
        else:
            logger.info("Validation successful. All required files and directories are present.")
            return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print('Usage: python bids_validator.py "/path/to/bids/dataset"')
        sys.exit(1)
    
    root_path = sys.argv[1]
    validator = BIDSValidator(root_path)
    result = validator.validate_file_structure()
    
    if result:
        print(f"OUTPUT: true", flush=True)
    else:
        print(f"OUTPUT: false", flush=True)
