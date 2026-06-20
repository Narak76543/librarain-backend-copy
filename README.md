# FastAPI Testing Project 01

## Overview

This is a FastAPI-based project designed for testing purposes. Follow the steps below to set up and run the application locally.

## Setup Instructions

1. **Clone the Project**
   - Clone the project from this repository:
     ```bash
     git clone git@gitlab.com:sdok-s-group/fastapitesting.git
     ```

2. **Create .env File**
   - Create a `.env` file from `.env.example` and update the configuration:
     ```bash
     cp .env.example .env
     ```

3. **Create Virtual Environment**
   - Create a virtual environment:
     ```bash
     python3 -m venv venv
     ```

4. **Activate Virtual Environment**
   - Activate the virtual environment:
     ```bash
     source venv/bin/activate
     ```

5. **Install Project Requirements**
   - Install the required dependencies:
     ```bash
     pip install -r requirements.txt
     ```

6. **Run the Project**
   - Run the application using Uvicorn:
     ```bash
     uvicorn main:app --reload
     ```

## Additional Information

- Ensure Python 3.8 or higher is installed on your system.
- Make sure the `.env` file contains the correct configurations to avoid runtime issues.
- For further assistance, please contact the project maintainers.# neak_arn_backend
