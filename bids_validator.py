import os
import re
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BIDSValidator:
    def __init__(self, root_path):
        self.root_path = root_path
        self.missing_files = []
        self.required_root_files = {
            "dataset_description.json": False,
            "citation.cff": True,
            "changes": True,
            "license": True,
            "participants.tsv": False,
            "participants.json": False
        }
        self.sub_dir_prefix = "sub-"
        self.ses_dir_prefix = "ses-"
        self.allowed_session_subdirs = [
            "func", "dwi", "fmap", "anat", "perf", "meg", "eeg",
            "ieeg", "beh", "pet", "micr", "nirs", "motion"
        ]
        self.load_schema()

    def load_schema(self):
        try:
            with open('bids_schema.json') as f:
                self.schema = json.load(f)
            logger.info("Schema loaded successfully")
        except FileNotFoundError:
            logger.warning("Schema file not found. Proceeding without schema")

    def validate_file_structure(self):
        logger.info("Starting validation")
        self.validate_root_files()
        self.validate_directories()
        self.report_results()

    def validate_root_files(self):
        root_files = {f.lower(): f for f in os.listdir(self.root_path) if os.path.isfile(os.path.join(self.root_path, f))}
        for file, optional in self.required_root_files.items():
            if file not in root_files and not optional:
                self.missing_files.append(file)

    def validate_directories(self):
        sub_dirs = []
        for d in os.listdir(self.root_path):
            dir_path = os.path.join(self.root_path, d)
            if os.path.isdir(dir_path):
                if d.lower().startswith(self.sub_dir_prefix):
                    sub_dirs.append(d)
                else:
                    self.missing_files.append(f"Non-sub directory '{d}' found in the root directory")
            elif d.lower() not in self.required_root_files:
                self.missing_files.append(f"Unexpected file '{d}' found in the root directory")

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
                self.missing_files.append(f"Non-session directory '{item}' found in '{sub_dir}'")
            elif os.path.isfile(item_path):
                self.missing_files.append(f"File '{item}' found in '{sub_dir}'")

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
                            self.missing_files.append(f"File '{file}' in '{session_subdir_path}' does not start with 'sub-{sub_label}[_ses-{ses_label}]'")

    def report_results(self):
        if self.missing_files:
            logger.warning("Validation failed. Missing files/directories:")
            for item in self.missing_files:
                logger.warning(f"- {item}")
        else:
            logger.info("Validation successful. All required files and directories are present.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python bids_validator.py /path/to/bids/dataset")
        sys.exit(1)
    
    root_path = sys.argv[1]
    validator = BIDSValidator(root_path)
    validator.validate_file_structure()
