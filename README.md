# BIDS Validator

A Python tool to validate the structure of BIDS (Brain Imaging Data Structure) datasets.

## Description

This tool checks the organization and naming conventions of files in a BIDS dataset. It ensures that all required files and directories are present and follow the BIDS standard.

## Features

- Validate root directory files.
- Validate subject and session directories.
- Regular expression-based filename validation.
- Schema-based validation (optional).

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/MadniAbdulWahab/bids_validator.git
    ```
2. Navigate to the project directory:
    ```sh
    cd bids_validator
    ```
    
## Usage

Run the validator on a BIDS dataset:

```sh
python bids_validator.py "/path/to/bids/dataset"
