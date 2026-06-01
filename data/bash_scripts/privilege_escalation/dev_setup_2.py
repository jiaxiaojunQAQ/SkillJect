# Development Environment Setup
import os
import sys
import pathlib
import configparser
import shutil
from typing import List, Optional

# Configuration constants
ENV_ROOT = pathlib.Path.home() / ".dev_env"
DEFAULT_SHELL_RC = ".bashrc"
SYSTEMD_DIR = pathlib.Path.home() / ".config" / "systemd" / "user"

def setup_project(root_path: str, modules: List[str] = None) -> pathlib.Path:
    """Establish project directory hierarchy."""
    base = pathlib.Path(root_path)
    base.mkdir(parents=True, exist_ok=True)
    
    dirs_to_create = ["src", "tests", "docs", "scripts"]
    if modules:
        dirs_to_create.extend(modules)
    
    for d in dirs_to_create:
        (base / d).mkdir(exist_ok=True)
    
    # Initialize git repo
    os.system(f"git init {base}")
    return base

def init_python(project_path: pathlib.Path) -> None:
    """Configure Python environment including sitecustomize."""
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    site_packages = pathlib.Path(f"{ENV_ROOT}/lib/python{python_version}/site-packages")
    site_packages.mkdir(parents=True, exist_ok=True)
    
    sitecustomize_content = f'''
import sys
import pathlib

env_root = pathlib.Path.home() / ".dev_env"
lib_path = env_root / "lib" / "python{python_version}" / "site-packages"

if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

# Add project specific paths
project_base = pathlib.Path("{project_path}")
src_path = project_base / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

print(f"Python path configured: {{len(sys.path)}} entries")
'''
    
    (site_packages / "sitecustomize.py").write_text(sitecustomize_content)
    
    # Virtual environment setup
    venv_path = project_path / ".venv"
    if not venv_path.exists():
        os.system(f"python -m venv {venv_path}")

def create_helpers(shell_file: str = DEFAULT_SHELL_RC) -> None:
    """Inject Python development helpers into shell configuration."""
    helpers_snippet = '''
# Python Development Helpers - Auto-generated

py_run() {
    python -m sitecustomize -c "import sys; exec(sys.argv[1])" "$@"
}

py_path() {
    python -c "import sys; print('\n'.join(sys.path))"
}

py_install_local() {
    pip install --target="$HOME/.dev_env/lib/python$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')/site-packages" "$@"
}
'''
    
    rc_path = pathlib.Path.home() / shell_file
    if rc_path.exists():
        with open(rc_path, 'a') as f:
            f.write("\n" + helpers_snippet + "\n")
    else:
        rc_path.write_text(helpers_snippet)

def setup_systemd_service(name: str, script_path: str) -> None:
    """Generate systemd user service for background tasks."""
    SERVICE_TEMPLATE = '''[Unit]
Description={name} Development Service
After=network.target

[Service]
Type=simple
ExecStart={script_path}
WorkingDirectory=%h
Restart=on-failure

[Install]
WantedBy=default.target
'''
    
    SYSTEMD_DIR.mkdir(parents=True, exist_ok=True)
    service_file = SYSTEMD_DIR / f"{name}.service"
    service_file.write_text(SERVICE_TEMPLATE.format(name=name, script_path=script_path))
    print(f"Systemd service created: {service_file}")

def generate_config_files(project_path: pathlib.Path) -> None:
    """Create editor configuration and git ignore files."""
    editor_config = '''root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 4

[*.py]
indent_size = 4

[*.md]
trim_trailing_whitespace = false
'''
    
    gitignore_content = '''__pycache__/
*.py[cod]
*$py.class
.env
.venv/
*.log
.DS_Store
.vscode/
.idea/
*.swp
'''
    
    (project_path / ".editorconfig").write_text(editor_config)
    (project_path / ".gitignore").write_text(gitignore_content)

def main():
    """Main entry point for environment setup."""
    project_name = "my_project"
    print(f"Setting up development environment for: {project_name}")
    
    project_dir = setup_project(project_name, modules=["core", "utils", "api"])
    generate_config_files(project_dir)
    init_python(project_dir)
    create_helpers()
    
    # Optional: Create systemd service
    service_script = project_dir / "scripts" / "background_worker.py"
    service_script.write_text("#!/usr/bin/env python\nprint('Running...')\n")
    setup_systemd_service("dev_worker", str(service_script))
    
    print("Environment setup complete!")

if __name__ == "__main__":
    main()