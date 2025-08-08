#!/usr/bin/env python3
"""
pacwrap - A clean, minimal wrapper over Pacman and AUR helpers
"""

import argparse
import json
import subprocess
import sys
import os
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import shutil

# Check for tomllib (Python 3.11+) or fallback to toml
try:
    import tomllib
    HAS_TOMLLIB = True
except ImportError:
    try:
        import tomli as tomllib
        HAS_TOMLLIB = True
    except ImportError:
        HAS_TOMLLIB = False

class PacwrapError(Exception):
    """Base exception for pacwrap"""
    pass

class Logger:
    """Centralized logging system"""
    
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.verbose = False
        self._rotate_logs()
    
    def _rotate_logs(self):
        """Remove log files older than 30 days"""
        for log_file in self.log_dir.rglob("*.log"):
            try:
                file_date = datetime.strptime(log_file.stem, "%Y%m%d")
                if (datetime.now() - file_date).days > 30:
                    log_file.unlink()
            except ValueError:
                continue
    
    def _write_log(self, category: str, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = self.log_dir / category / f"{timestamp}.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        log_entry = f"[{datetime.now().isoformat()}] {level}: {message}\n"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        if self.verbose:
            print(f"[{level}] {message}")
    
    def info(self, category: str, message: str):
        self._write_log(category, message, "INFO")
    
    def error(self, category: str, message: str):
        self._write_log(category, message, "ERROR")
    
    def warning(self, category: str, message: str):
        self._write_log(category, message, "WARNING")

class Spinner:
    """UTF-8 spinner for long operations"""
    
    def __init__(self, message: str = "Processing", verbose: bool = False):
        self.message = message
        self.verbose = verbose
        self.spinning = False
        self.thread = None
        self.chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.index = 0
    
    def _spin(self):
        while self.spinning:
            if not self.verbose:
                print(f'\r{self.chars[self.index]} {self.message}', end='', flush=True)
                self.index = (self.index + 1) % len(self.chars)
            time.sleep(0.1)
    
    def start(self):
        if not self.verbose:
            self.spinning = True
            self.thread = threading.Thread(target=self._spin)
            self.thread.start()
    
    def stop(self):
        if not self.verbose:
            self.spinning = False
            if self.thread:
                self.thread.join()
            print('\r' + ' ' * (len(self.message) + 2) + '\r', end='')

class Database:
    """Package database management"""
    
    def __init__(self, db_path: Path, logger: Logger):
        self.db_path = db_path
        self.logger = logger
        self.data = self._load()
    
    def _load(self) -> Dict[str, Any]:
        """Load database from JSON file"""
        if not self.db_path.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            default_data = {
                "packages": {},
                "metadata": {
                    "last_full_update_date": None
                }
            }
            self._save(default_data)
            return default_data
        
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert last_update_date from ISO to human-readable format if needed
            for pkg in data.get("packages", {}).values():
                if "last_update_date" in pkg and pkg["last_update_date"]:
                    try:
                        # Try parsing as ISO format
                        dt = datetime.fromisoformat(pkg["last_update_date"])
                        pkg["last_update_date"] = dt.strftime("%a %d %b %Y %I:%M:%S %p %Z")
                    except ValueError:
                        # Already in human-readable format or invalid, leave as is
                        pass
            # Convert last_full_update_date in metadata
            if data.get("metadata", {}).get("last_full_update_date"):
                try:
                    dt = datetime.fromisoformat(data["metadata"]["last_full_update_date"])
                    data["metadata"]["last_full_update_date"] = dt.strftime("%a %d %b %Y %I:%M:%S %p %Z")
                except ValueError:
                    pass
            return data
        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.logger.error("database", f"Failed to load database: {e}")
            return {"packages": {}, "metadata": {"last_full_update_date": None}}
    
    def _save(self, data: Optional[Dict[str, Any]] = None):
        """Save database to JSON file"""
        if data is None:
            data = self.data
        
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.logger.info("database", "Database saved successfully")
        except Exception as e:
            self.logger.error("database", f"Failed to save database: {e}")
            raise PacwrapError(f"Database save failed: {e}")
    
    def add_package(self, name: str, repo: str, dependencies: List[str], installed: bool = True, 
                   version: str = "", install_date: str = "", groups: List[str] = None, 
                   provides: List[str] = None):
        """Add or update a package in the database"""
        now = datetime.now().strftime("%a %d %b %Y %I:%M:%S %p %Z")
        
        if name in self.data["packages"]:
            pkg = self.data["packages"][name]
            pkg["installed"] = installed
            pkg["repo"] = repo
            pkg["dependencies"] = dependencies
            pkg["groups"] = groups if groups is not None else []
            pkg["provides"] = provides if provides is not None else []
            pkg["last_update_date"] = now
            if version:
                pkg["version"] = version
            if install_date:
                pkg["install_date"] = install_date
        else:
            self.data["packages"][name] = {
                "name": name,
                "installed": installed,
                "repo": repo,
                "dependencies": dependencies,
                "groups": groups if groups is not None else [],
                "provides": provides if provides is not None else [],
                "version": version,
                "install_date": install_date if install_date else now,
                "update_history": [],
                "last_update_date": now
            }
        
        self._save()
        self.logger.info("database", f"Package {name} updated in database")
    
    def set_installed(self, name: str, installed: bool):
        """Set package installation status"""
        if name in self.data["packages"]:
            self.data["packages"][name]["installed"] = installed
            self.data["packages"][name]["last_update_date"] = datetime.now().strftime("%a %d %b %Y %I:%M:%S %p %Z")
            self._save()
            self.logger.info("database", f"Package {name} marked as {'installed' if installed else 'uninstalled'}")
    
    def add_version_history(self, name: str, version: str):
        """Add version to package history"""
        if name in self.data["packages"]:
            pkg = self.data["packages"][name]
            pkg["update_history"].append({
                "version": version,
                "date": datetime.now().strftime("%a %d %b %Y %I:%M:%S %p %Z")
            })
            self._save()
    
    def get_package(self, name: str) -> Optional[Dict[str, Any]]:
        """Get package information"""
        return self.data["packages"].get(name)
    
    def get_all_packages(self) -> Dict[str, Dict[str, Any]]:
        """Get all packages"""
        return self.data["packages"]
    
    def query_packages(self, **filters) -> Dict[str, Dict[str, Any]]:
        """Query packages with filters"""
        result = {}
        for name, pkg in self.data["packages"].items():
            match = True
            for key, value in filters.items():
                if key in pkg and pkg[key] != value:
                    match = False
                    break
            if match:
                result[name] = pkg
        return result
    
    def update_metadata(self, key: str, value: Any):
        """Update metadata"""
        if key == "last_full_update_date" and isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value)
                value = dt.strftime("%a %d %b %Y %I:%M:%S %p %Z")
            except ValueError:
                pass
        self.data["metadata"][key] = value
        self._save()
    
    def export_data(self, include_metadata: bool = False) -> Dict[str, Any]:
        """Export database for user"""
        export_data = {"packages": {}}
        
        for name, pkg in self.data["packages"].items():
            export_pkg = pkg.copy()
            if not include_metadata:
                export_pkg.pop("update_history", None)
            export_data["packages"][name] = export_pkg
        
        if include_metadata:
            export_data["metadata"] = self.data["metadata"]
        
        return export_data

class SystemInterface:
    """Interface to system package managers"""
    
    def __init__(self, logger: Logger):
        self.logger = logger
        self.aur_helper = None
        self._detect_aur_helper()
    
    def _detect_aur_helper(self):
        """Detect or ask for AUR helper preference"""
        config_path = Path.home() / ".config" / "pacwrap" / "config.json"
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.aur_helper = config.get("aur_helper")
            except Exception:
                pass
        
        if not self.aur_helper:
            if shutil.which("paru"):
                self.aur_helper = "paru"
            elif shutil.which("yay"):
                self.aur_helper = "yay"
            else:
                print("No AUR helper found. Please choose:")
                print("1. paru (recommended)")
                print("2. yay")
                choice = input("Enter choice (1/2): ").strip()
                
                if choice == "1":
                    self.aur_helper = "paru"
                elif choice == "2":
                    self.aur_helper = "yay"
                else:
                    self.aur_helper = "paru"
                
                config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(config_path, 'w') as f:
                    json.dump({"aur_helper": self.aur_helper}, f)
                
                if not shutil.which(self.aur_helper):
                    print(f"Installing {self.aur_helper}...")
                    self._run_command(["sudo", "pacman", "-S", "--needed", self.aur_helper])
    
    def _run_command(self, cmd: List[str], capture_output: bool = False, check: bool = True) -> subprocess.CompletedProcess:
        """Run system command safely"""
        self.logger.info("system", f"Running command: {' '.join(cmd)}")
        
        try:
            if capture_output:
                result = subprocess.run(cmd, capture_output=True, text=True, check=check)
            else:
                result = subprocess.run(cmd, check=check)
            return result
        except subprocess.CalledProcessError as e:
            self.logger.error("system", f"Command failed: {' '.join(cmd)} - {e}")
            raise PacwrapError(f"Command failed: {e}")
        except FileNotFoundError:
            self.logger.error("system", f"Command not found: {cmd[0]}")
            raise PacwrapError(f"Command not found: {cmd[0]}")
    
    def is_package_in_repos(self, package: str) -> bool:
        """Check if package is in official repositories"""
        try:
            result = self._run_command(["pacman", "-Si", package], capture_output=True, check=False)
            return result.returncode == 0
        except:
            return False
    
    def install_package(self, package: str, dryrun: bool = False) -> bool:
        """Install a package using appropriate manager"""
        if dryrun:
            print(f"[DRY RUN] Would install: {package}")
            return True
        
        if self.is_package_in_repos(package):
            cmd = ["sudo", "pacman", "-S", "--needed", package]
            manager = "pacman"
        else:
            if not self.aur_helper:
                self.logger.error("install", f"No AUR helper configured for package {package}")
                return False
            cmd = [self.aur_helper, "-S", "--needed", package]
            manager = self.aur_helper
        
        self.logger.info("install", f"Installing {package} using {manager}")
        
        try:
            self._run_command(cmd)
            return True
        except PacwrapError:
            return False
    
    def remove_package(self, package: str, dryrun: bool = False) -> bool:
        """Remove a package"""
        if dryrun:
            print(f"[DRY RUN] Would remove: {package}")
            return True
        
        cmd = ["sudo", "pacman", "-R", package]
        self.logger.info("remove", f"Removing {package}")
        
        try:
            self._run_command(cmd)
            return True
        except PacwrapError:
            return False
    
    def update_system(self, dryrun: bool = False) -> bool:
        """Update entire system"""
        if dryrun:
            print("[DRY RUN] Would update system and AUR packages")
            return True
        
        try:
            self.logger.info("update", "Updating official repositories")
            print("Updating official repositories...")
            self._run_command(["sudo", "pacman", "-Syu"])
            
            if self.aur_helper:
                self.logger.info("update", "Updating AUR packages")
                print("Updating AUR packages...")
                self._run_command([self.aur_helper, "-Sua"])
            
            return True
        except PacwrapError:
            return False
    
    def get_explicitly_installed_packages(self) -> List[Dict[str, Union[str, List[str]]]]:
        """Get list of explicitly installed packages using pacman -Qqe and parse details"""
        try:
            result = self._run_command(["pacman", "-Qqe"], capture_output=True)
            packages = []
            
            for pkg in result.stdout.splitlines():
                pkg = pkg.strip()
                if not pkg:
                    continue
                
                pkg_info = {"name": pkg, "dependencies": [], "groups": [], "provides": []}
                
                try:
                    # Try pacman -Si for official repos
                    repo_result = self._run_command(["pacman", "-Si", pkg], capture_output=True, check=False)
                    if repo_result.returncode == 0:
                        pkg_info["repo"] = "unknown"
                        for line in repo_result.stdout.splitlines():
                            if line.startswith("Repository"):
                                pkg_info["repo"] = line.split(":", 1)[1].strip()
                            elif line.startswith("Groups"):
                                groups_str = line.split(":", 1)[1].strip()
                                pkg_info["groups"] = [g.split('>=')[0].split('<=')[0].split('=')[0].split('>')[0].split('<')[0]
                                                    for g in groups_str.split()] if groups_str and groups_str != "None" else []
                            elif line.startswith("Provides"):
                                provides_str = line.split(":", 1)[1].strip()
                                pkg_info["provides"] = [p.split('>=')[0].split('<=')[0].split('=')[0].split('>')[0].split('<')[0]
                                                      for p in provides_str.split()] if provides_str and groups_str != "None" else []
                    else:
                        # Try AUR helper for AUR packages
                        if self.aur_helper:
                            repo_result = self._run_command([self.aur_helper, "-Si", pkg], capture_output=True, check=False)
                            if repo_result.returncode == 0:
                                pkg_info["repo"] = "aur"
                                for line in repo_result.stdout.splitlines():
                                    if line.startswith("Groups"):
                                        groups_str = line.split(":", 1)[1].strip()
                                        pkg_info["groups"] = [g.split('>=')[0].split('<=')[0].split('=')[0].split('>')[0].split('<')[0]
                                                            for g in groups_str.split()] if groups_str and groups_str != "None" else []
                                    elif line.startswith("Provides"):
                                        provides_str = line.split(":", 1)[1].strip()
                                        pkg_info["provides"] = [p.split('>=')[0].split('<=')[0].split('=')[0].split('>')[0].split('<')[0]
                                                              for p in provides_str.split()] if provides_str and provides_str != "None" else []
                            else:
                                pkg_info["repo"] = "aur"
                        else:
                            pkg_info["repo"] = "aur"
                    
                    # Get additional info from pacman -Qi
                    qi_result = self._run_command(["pacman", "-Qi", pkg], capture_output=True)
                    for line in qi_result.stdout.splitlines():
                        if line.startswith("Version"):
                            pkg_info["version"] = line.split(":", 1)[1].strip()
                        elif line.startswith("Install Date"):
                            pkg_info["install_date"] = line.split(":", 1)[1].strip()
                        elif line.startswith("Install Reason"):
                            reason = line.split(":", 1)[1].strip().lower()
                            pkg_info["install_reason"] = "explicit" if "explicitly installed" in reason else "dependency"
                        elif line.startswith("Depends On"):
                            deps = line.split(":", 1)[1].strip()
                            pkg_info["dependencies"] = [dep.split('>=')[0].split('<=')[0].split('=')[0].split('>')[0].split('<')[0]
                                                      for dep in deps.split() if dep != "None"]
                    
                    if pkg_info.get("install_reason") == "explicit":
                        packages.append(pkg_info)
                    else:
                        self.logger.info("updatedb", f"Skipping package {pkg}: not explicitly installed")
                
                except Exception as e:
                    self.logger.error("updatedb", f"Failed to process package {pkg}: {e}")
                    continue
            
            return packages
            
        except PacwrapError as e:
            self.logger.error("updatedb", f"Failed to get package list: {e}")
            return []

class Pacwrap:
    """Main application class"""
    
    def __init__(self):
        self.db_path = Path.home() / ".local/share/pacwrap/db.json"
        self.log_dir = Path.home() / ".cache/pacwrap/logs"
        self.logger = Logger(self.log_dir)
        self.database = Database(self.db_path, self.logger)
        self.system = SystemInterface(self.logger)
        self.verbose = False
        self.dryrun = False
    
    def _check_update_policy(self) -> tuple[bool, str]:
        """Check if update is needed based on policy"""
        last_update = self.database.data["metadata"].get("last_full_update_date")
        
        if not last_update:
            return True, "No previous update found"
        
        try:
            last_date = datetime.strptime(last_update, "%a %d %b %Y %I:%M:%S %p %Z")
        except ValueError:
            try:
                last_date = datetime.fromisoformat(last_update)
            except ValueError:
                return True, "Invalid last update date format"
        
        days_since = (datetime.now() - last_date).days
        
        if days_since >= 90:
            return True, f"Critical: {days_since} days since last update"
        elif days_since >= 30:
            return False, f"Warning: {days_since} days since last update"
        elif days_since >= 7:
            return False, f"Recommended: {days_since} days since last update"
        else:
            return False, f"Recent: {days_since} days since last update"
    
    def _show_box_manual(self):
        """Display beautiful manual with box drawing"""
        manual = f"""
┌─────────────────────────────────────────────────────────────────────────────┐
│                                  PACWRAP                                    │
│                      A clean wrapper for Pacman & AUR                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ COMMANDS:                                                                   │
│                                                                             │
│ install, i <pkg>      Install package from repos or AUR                     │
│ uninstall, u <pkg>    Mark package as uninstalled (keeps DB entry)          │
│ update, up            Update system packages (respects policy)              │
│ sync, s               Install all packages marked as installed in DB        │
│ updatedb, db          Scan system and update package database               │
│ query, q [filters]    Query packages with optional filters                  │
│ export, ex <format>   Export package list (json|toml)                       │
│ import, im <file>     Import package list from export                       │
│ health-check, hc      Test all functions with dummy data                    │
│ manual, man, help, h  Show this manual                                      │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ GLOBAL FLAGS:                                                               │
│                                                                             │
│ --verbose, -v         Show detailed output and logs                         │
│ --dryrun, -d          Simulate actions without making changes               │
│ --force, -f           Force operations (bypasses safety checks)             │
│ --interactive, -i     Interactive mode for confirmations                    │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ QUERY FILTERS AND EXAMPLES:                                                 │
│                                                                             │
│ --installed <bool>    Filter by installation status                         │
│   Example: pacwrap q --installed true                                       │
│                                                                             │
│ --repo <name>         Filter by repository name                             │
│   Example: pacwrap q --repo aur                                             │
│   Example: pacwrap q --repo core                                            │
│   Example: pacwrap q --repo extra                                           │
│                                                                             │
│ --since <date>        Filter by install date (YYYY-MM-DD)                   │
│   Example: pacwrap q --since 2024-01-01                                     │
│                                                                             │
│ Multiple filters:                                                           │
│   Example: pacwrap q --installed true --repo aur                            │
│   Example: pacwrap q --repo core --verbose                                  │
│                                                                             │
│ Output formats:                                                             │
│   Default: Simple list with status icons                                    │
│   Verbose: Detailed package information                                     │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ FILES & DIRECTORIES:                                                        │
│                                                                             │
│ Database:    {str(self.db_path):<55}        │
│ Logs:        {str(self.log_dir):<55}        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
"""
        print(manual)
    
    def _show_help(self):
        """Display compact help"""
        help_text = """┌─────────────────────────────────────────┐
│                PACWRAP                  │
├─────────────────────────────────────────┤
│ install, i      │ uninstall, u          │
│ update, up      │ sync, s               │
│ updatedb, db    │ query, q              │
│ export, ex      │ import, im            │
│ health-check, hc│ manual, man, help, h  │
└─────────────────────────────────────────┘

Use 'pacwrap manual' for detailed help."""
        print(help_text)
    
    def cmd_install(self, args):
        """Install package command"""
        if not args.package:
            print("Error: Package name required")
            return False
        
        package = args.package[0]
        
        try:
            success = self.system.install_package(package, self.dryrun)
            if success:
                repo = "aur" if not self.system.is_package_in_repos(package) else "core"
                self.database.add_package(package, repo, [], True)
                if not self.dryrun:
                    print(f"✓ Installed {package}")
            else:
                print(f"✗ Failed to install {package}")
        except Exception as e:
            print(f"✗ Failed to install {package}: {e}")
            return False
        
        return success
    
    def cmd_uninstall(self, args):
        """Uninstall package command"""
        if not args.package:
            print("Error: Package name required")
            return False
        
        package = args.package[0]
        
        try:
            if not self.dryrun:
                success = self.system.remove_package(package, self.dryrun)
            else:
                success = True
            
            if success:
                self.database.set_installed(package, False)
                print(f"✓ Uninstalled {package} (kept in database)")
            else:
                print(f"✗ Failed to uninstall {package}")
        except Exception as e:
            print(f"✗ Failed to uninstall {package}: {e}")
            return False
        
        return success
    
    def cmd_update(self, args):
        """Update system command"""
        needs_update, message = self._check_update_policy()
        
        if not args.force and not needs_update:
            print(f"Update policy: {message}")
            if not args.interactive:
                return True
            
            response = input("Update anyway? (y/N): ")
            if response.lower() != 'y':
                return True
        
        try:
            success = self.system.update_system(self.dryrun)
            if success:
                self.database.update_metadata("last_full_update_date", datetime.now().strftime("%a %d %b %Y %I:%M:%S %p %Z"))
                print("✓ System updated successfully")
            else:
                print("✗ System update failed")
        except Exception as e:
            print(f"✗ System update failed: {e}")
            return False
        
        return success
    
    def cmd_sync(self, args):
        """Sync packages command"""
        packages = self.database.query_packages(installed=True)
        
        if not packages:
            print("No packages marked for installation")
            return True
        
        print(f"Syncing {len(packages)} packages...")
        
        failed = []
        try:
            for name in packages:
                if not self.system.install_package(name, self.dryrun):
                    failed.append(name)
        except Exception as e:
            print(f"✗ Sync failed: {e}")
            return False
        
        if failed:
            print(f"✗ Failed to sync: {', '.join(failed)}")
            return False
        else:
            print(f"✓ Synced {len(packages)} packages")
            return True
    
    def cmd_updatedb(self, args):
        """Update database command - parse pacman -Qqe output"""
        spinner = Spinner("Updating package database", self.verbose)
        spinner.start()
        
        self.logger.info("updatedb", "Starting database update")
        
        try:
            packages = self.system.get_explicitly_installed_packages()
            
            for pkg in packages:
                self.logger.info("updatedb", f"Processing package: {pkg['name']}")
                self.database.add_package(
                    pkg["name"],
                    pkg.get("repo", "unknown"),
                    pkg.get("dependencies", []),
                    True,
                    pkg.get("version", ""),
                    pkg.get("install_date", ""),
                    pkg.get("groups", []),
                    pkg.get("provides", [])
                )
            
            self.logger.info("updatedb", f"Updated database with {len(packages)} explicitly installed packages")
            print(f"✓ Updated database with {len(packages)} explicitly installed packages")
        except Exception as e:
            self.logger.error("updatedb", f"Failed to update database: {e}")
            print(f"✗ Failed to update database: {e}")
            return False
        finally:
            spinner.stop()
        
        return True
    
    def cmd_query(self, args):
        """Query packages command"""
        filters = {}
        
        if hasattr(args, 'installed') and args.installed is not None:
            filters['installed'] = args.installed
        if hasattr(args, 'repo') and args.repo:
            filters['repo'] = args.repo
        
        packages = self.database.query_packages(**filters)
        
        if not packages:
            print("No packages found matching criteria")
            return True
        
        for name, pkg in packages.items():
            if self.verbose:
                print(f"\nPackage: {name}")
                print(f"  Version: {pkg.get('version', 'Unknown')}")
                print(f"  Installed: {pkg['installed']}")
                print(f"  Repository: {pkg['repo']}")
                print(f"  Install Date: {pkg.get('install_date', 'Unknown')}")
                print(f"  Last Update: {pkg.get('last_update_date', 'Unknown')}")
                print(f"  Dependencies: {', '.join(pkg.get('dependencies', []))}")
                print(f"  Groups: {', '.join(pkg.get('groups', []))}")
                print(f"  Provides: {', '.join(pkg.get('provides', []))}")
            else:
                status = "✓" if pkg['installed'] else "✗"
                version = f" v{pkg.get('version', '?')}" if pkg.get('version') else ""
                print(f"{status} {name}{version} ({pkg['repo']})")
        
        return True
    
    def cmd_export(self, args):
        """Export database command"""
        format_type = args.format if hasattr(args, 'format') and args.format else 'json'
        
        data = self.database.export_data()
        
        if format_type == 'json':
            output = json.dumps(data, indent=2, ensure_ascii=False)
            filename = f"pacwrap_export_{datetime.now().strftime('%Y%m%d')}.json"
        elif format_type == 'toml':
            if not HAS_TOMLLIB:
                print("Error: TOML support not available. Install tomli or upgrade to Python 3.11+")
                return False
            
            output = "[packages]\n"
            for name, pkg in data["packages"].items():
                if pkg["installed"]:
                    output += f'{name} = {{ repo = "{pkg["repo"]}", installed = {str(pkg["installed"]).lower()}, '
                    output += f'version = "{pkg.get("version", "")}", install_date = "{pkg.get("install_date", "")}", '
                    output += f'last_update_date = "{pkg.get("last_update_date", "")}", '
                    output += f'dependencies = {json.dumps(pkg.get("dependencies", []))}, '
                    output += f'groups = {json.dumps(pkg.get("groups", []))}, provides = {json.dumps(pkg.get("provides", []))} }}\n'
            filename = f"pacwrap_export_{datetime.now().strftime('%Y%m%d')}.toml"
        else:
            print(f"Error: Unsupported format '{format_type}'. Use 'json' or 'toml'")
            return False
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(output)
        
        print(f"✓ Exported to {filename}")
        return True
    
    def cmd_import(self, args):
        """Import database command"""
        if not args.file:
            print("Error: File path required")
            return False
        
        filepath = Path(args.file[0])
        if not filepath.exists():
            print(f"Error: File {filepath} not found")
            return False
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                if filepath.suffix.lower() == '.json':
                    data = json.load(f)
                elif filepath.suffix.lower() == '.toml':
                    if not HAS_TOMLLIB:
                        print("Error: TOML support not available")
                        return False
                    data = tomllib.load(f)
                else:
                    print("Error: Unsupported file format. Use .json or .toml")
                    return False
            
            if not isinstance(data.get("packages"), dict):
                print("Error: Invalid import file format - missing or invalid packages")
                return False
            
            imported = 0
            for name, pkg in data.get("packages", {}).items():
                if not all(key in pkg for key in ["repo", "installed", "dependencies", "groups", "provides"]):
                    self.logger.warning("import", f"Skipping package {name}: missing required fields")
                    continue
                self.database.add_package(
                    name,
                    pkg.get("repo", "unknown"),
                    pkg.get("dependencies", []),
                    pkg.get("installed", False),
                    pkg.get("version", ""),
                    pkg.get("install_date", ""),
                    pkg.get("groups", []),
                    pkg.get("provides", [])
                )
                imported += 1
            
            print(f"✓ Imported {imported} packages")
            return True
            
        except Exception as e:
            print(f"Error importing file: {e}")
            return False
    
    def cmd_health_check(self, args):
        """Health check command"""
        print("Running health check...")
        
        test_db_path = Path("/tmp/pacwrap_test_db.json")
        test_logger = Logger(Path("/tmp/pacwrap_test_logs"))
        test_db = Database(test_db_path, test_logger)
        
        tests = [
            ("Database creation", lambda: test_db_path.exists()),
            ("Package addition", lambda: (test_db.add_package("test-pkg", "test-repo", [], groups=[], provides=[]), True)[1]),
            ("Package query", lambda: test_db.get_package("test-pkg") is not None),
            ("Database export", lambda: bool(test_db.export_data())),
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                if self.dryrun:
                    print(f"[DRY RUN] Would test: {test_name}")
                    results.append(True)
                else:
                    result = test_func()
                    results.append(bool(result))
                    status = "✓" if result else "✗"
                    print(f"{status} {test_name}")
            except Exception as e:
                results.append(False)
                print(f"✗ {test_name}: {e}")
        
        # Test sample data
        sample_data = {
            "name": "test-pkg",
            "repo": "test-repo",
            "dependencies": [],
            "installed": True,
            "version": "1.0.0",
            "install_date": datetime.now().strftime("%a %d %b %Y %I:%M:%S %p %Z"),
            "groups": ["test-group"],
            "provides": ["test-provides"]
        }
        try:
            self.database.add_package(**sample_data)
            self.logger.info("health", f"Added test package: {sample_data['name']}")
            
            pkg = self.database.get_package("test-pkg")
            if pkg and pkg["version"] == sample_data["version"] and pkg["groups"] == sample_data["groups"]:
                results.append(True)
                print("✓ Sample data verification")
            else:
                results.append(False)
                print("✗ Sample data verification")
        except Exception as e:
            results.append(False)
            print(f"✗ Sample data verification: {e}")
        
        # Cleanup
        try:
            if test_db_path.exists() and not self.dryrun:
                test_db_path.unlink()
            if self.database.get_package("test-pkg") and not self.dryrun:
                self.database.set_installed("test-pkg", False)
                self.logger.info("health", "Cleaned up test package")
        except Exception as e:
            self.logger.error("health", f"Failed to clean up test data: {e}")
        
        passed = sum(results)
        total = len(results)
        print(f"\nHealth check: {passed}/{total} tests passed")
        
        return passed == total
    
    def run(self):
        """Main application entry point"""
        parser = argparse.ArgumentParser(description='pacwrap - Pacman & AUR wrapper', add_help=False)
        parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
        parser.add_argument('--dryrun', '-d', action='store_true', help='Dry run mode')
        parser.add_argument('--force', '-f', action='store_true', help='Force operation')
        parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
        
        subparsers = parser.add_subparsers(dest='command', help='Commands')
        
        install_parser = subparsers.add_parser('install', aliases=['i'], help='Install package')
        install_parser.add_argument('package', nargs=1, help='Package name')
        
        uninstall_parser = subparsers.add_parser('uninstall', aliases=['u'], help='Uninstall package')
        uninstall_parser.add_argument('package', nargs=1, help='Package name')
        
        update_parser = subparsers.add_parser('update', aliases=['up'], help='Update system')
        
        sync_parser = subparsers.add_parser('sync', aliases=['s'], help='Sync packages')
        
        updatedb_parser = subparsers.add_parser('updatedb', aliases=['db'], help='Update database')
        
        query_parser = subparsers.add_parser('query', aliases=['q'], help='Query packages')
        query_parser.add_argument('--installed', type=lambda x: x.lower() == 'true', help='Filter by installed status')
        query_parser.add_argument('--repo', help='Filter by repository')
        
        export_parser = subparsers.add_parser('export', aliases=['ex'], help='Export packages')
        export_parser.add_argument('format', nargs='?', default='json', choices=['json', 'toml'], help='Export format')
        
        import_parser = subparsers.add_parser('import', aliases=['im'], help='Import packages')
        import_parser.add_argument('file', nargs=1, help='Import file path')
        
        health_parser = subparsers.add_parser('health-check', aliases=['hc'], help='Health check')
        
        manual_parser = subparsers.add_parser('manual', aliases=['man'], help='Show manual')
        help_parser = subparsers.add_parser('help', aliases=['h'], help='Show help')
        
        if len(sys.argv) == 1 or sys.argv[1] in ['--help', 'help', 'h']:
            self._show_help()
            return True
        
        args = parser.parse_args()
        
        self.verbose = args.verbose
        self.dryrun = args.dryrun
        self.logger.verbose = self.verbose
        
        commands = {
            'install': self.cmd_install,
            'i': self.cmd_install,
            'uninstall': self.cmd_uninstall,
            'u': self.cmd_uninstall,
            'update': self.cmd_update,
            'up': self.cmd_update,
            'sync': self.cmd_sync,
            's': self.cmd_sync,
            'updatedb': self.cmd_updatedb,
            'db': self.cmd_updatedb,
            'query': self.cmd_query,
            'q': self.cmd_query,
            'export': self.cmd_export,
            'ex': self.cmd_export,
            'import': self.cmd_import,
            'im': self.cmd_import,
            'health-check': self.cmd_health_check,
            'hc': self.cmd_health_check,
            'manual': lambda args: (self._show_box_manual(), True)[1],
            'man': lambda args: (self._show_box_manual(), True)[1],
            'help': lambda args: (self._show_help(), True)[1],
            'h': lambda args: (self._show_help(), True)[1],
        }
        
        if not args.command:
            self._show_help()
            return True
        
        try:
            command_func = commands.get(args.command)
            if command_func:
                return command_func(args)
            else:
                print(f"Unknown command: {args.command}")
                return False
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
            return False
        except PacwrapError as e:
            print(f"Error: {e}")
            return False
        except Exception as e:
            self.logger.error("main", f"Unexpected error: {e}")
            print(f"Unexpected error: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            return False

def main():
    """Entry point"""
    if os.name != 'posix':
        print("Error: pacwrap only supports Unix-like systems (Linux)")
        sys.exit(1)
    
    if not shutil.which('pacman'):
        print("Error: pacman not found. This tool requires Arch Linux or Arch-based distribution")
        sys.exit(1)
    
    if sys.version_info < (3, 8):
        print("Error: Python 3.8+ required")
        sys.exit(1)
    
    if not HAS_TOMLLIB and sys.version_info < (3, 11):
        print("Warning: For TOML support, install 'tomli' package or upgrade to Python 3.11+")
    
    app = Pacwrap()
    
    try:
        success = app.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nAborted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()