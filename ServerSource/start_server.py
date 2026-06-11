import os
import sys
import subprocess
import venv

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    venv_dir = os.path.join(base_dir, 'venv')
    
    # Check if venv exists, create if not
    if not os.path.exists(venv_dir):
        print("Creating virtual environment...")
        venv.create(venv_dir, with_pip=True)
    
    # Get paths to python and pip in venv
    if os.name == 'nt':
        pip_exe = os.path.join(venv_dir, 'Scripts', 'pip.exe')
        python_exe = os.path.join(venv_dir, 'Scripts', 'python.exe')
    else:
        pip_exe = os.path.join(venv_dir, 'bin', 'pip')
        python_exe = os.path.join(venv_dir, 'bin', 'python')
    
    # Install dependencies
    requirements_file = os.path.join(base_dir, 'requirements.txt')
    if os.path.exists(requirements_file):
        print("Verifying and installing dependencies...")
        subprocess.check_call([pip_exe, 'install', '-r', requirements_file])
    else:
        print("requirements.txt not found! Skipping dependencies installation.")

    app_file = os.path.join(base_dir, 'app.py')
    
    print("\nStarting MariaDB service...")
    try:
        subprocess.check_call(['sudo', 'systemctl', 'start', 'mariadb'])
    except subprocess.CalledProcessError:
        print("Failed to start MariaDB service. Please ensure you have sudo privileges.")
        sys.exit(1)

    print("\nConfiguring MariaDB user...")
    try:
        # Create user idempotently. 
        mariadb_command = "CREATE USER IF NOT EXISTS 'bazar_user'@'localhost' IDENTIFIED BY 'bazar_pass'; GRANT ALL PRIVILEGES ON *.* TO 'bazar_user'@'localhost'; FLUSH PRIVILEGES;"
        subprocess.check_call(['sudo', 'mariadb', '-u', 'root', '-e', mariadb_command])
    except subprocess.CalledProcessError:
        print("Warning: Failed to auto-configure MariaDB user. It might already be set up, or requires manual intervention.")

    print("\nInitializing database schema and seed data...")
    try:
        setup_script = "from app import init_db_internal; init_db_internal()"
        subprocess.check_call([python_exe, '-c', setup_script])
    except Exception as e:
        print(f"Warning: Failed to run initial DB setup: {e}")

    print("\n=============================================")
    print("Starting Flask application...")
    print("=============================================\n")
    
    try:
        # Start the app using the virtual environment's python
        subprocess.check_call([python_exe, app_file])
    except KeyboardInterrupt:
        print("\nShutting down Flask application...")
    finally:
        print("Stopping MariaDB service...")
        subprocess.call(['sudo', 'systemctl', 'stop', 'mariadb'])

if __name__ == '__main__':
    main()
