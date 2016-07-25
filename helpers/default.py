#!/usr/bin/env python

##############################################################################
# DO NOT MODIFY THIS FILE. Instead, modify 'helpers/custom'.
##############################################################################

import sys
import os
import subprocess
import shutil
import random
import string

COOKBOOK_NAME = sys.argv[0]
if os.environ.get('SHOESTRAP_BASE') is None:
  os.chdir(os.path.dirname(COOKBOOK_NAME))
  DIR = os.getcwd()
else:
  DIR = os.environ.get('SHOESTRAP_BASE')

COOKBOOK_NAME = os.path.basename(COOKBOOK_NAME)

DEFAULT_ASSETS_PATH = ""
COOKBOOK_ASSETS_PATH = ""

#
# Run a given recipe.
#
# Arguments can be passed to the 'recipe' function. They will be accessible by
# the recipe via args[0], args[1], args[2], ...
#
def recipe(current_recipe_name, *args):
  global DEFAULT_ASSETS_PATH
  global COOKBOOK_ASSETS_PATH
  DEFAULT_ASSETS_PATH = "%s/assets/default/%s" % (DIR, current_recipe_name)
  COOKBOOK_ASSETS_PATH = "%s/assets/%s/%s" % (DIR, COOKBOOK_NAME, current_recipe_name)
  custom_recipe = "%s/recipes/custom/%s" % (DIR, current_recipe_name)
  default_recipe = "%s/recipes/default/%s" % (DIR, current_recipe_name)

  if os.path.isfile(custom_recipe):
    log("Running recipe '%s'..." % custom_recipe, 1)
    separator()
    execfile(custom_recipe)
  elif os.path.isfile(default_recipe):
    log("Running recipe '%s'..." % default_recipe, 1)
    separator()
    execfile(default_recipe)
  else:
    error("Could not find recipe for '%s'. Fail!", current_recipe_name)

  os.chdir(DIR)

#
# Prints the 'finished' banner.
#
def finished():
  spacer(1)
  separator("=")
  print(" FINISHED: '%s'" % COOKBOOK_NAME)
  separator("=")
  spacer(1)

#
# Writes a log line to the screen
#
# If specified, the first parameter is the number of empty lines to print
# before the log message.
#
# If specified, the second parameter is the number of empty lines to print
# before the log message.
#
def log(message, empty_lines_before=0, empty_lines_after=0):
  if empty_lines_before > 0:
    spacer(empty_lines_before)

  print(" * " + str(message))

  if empty_lines_after > 0:
    spacer(empty_lines_after)

#
# Writes an error log line to the screen and exit with an error code.
#
def error(message):
  spacer(2)
  print(" -> " + str(message))
  spacer(2)
  sys.exit(1)

#
# Write one or many empty lines to the screen.
#
def spacer(spaces=1):
  for _ in range(0, spaces):
    print

#
# noop
#
def noop():
  pass

#
# Write a separator to the screen.
#
# You can optionally specify the separator character. Default is '-'.
#
def separator(char='-'):

  width = int(subprocess.Popen("tput cols", shell=True, stdout=subprocess.PIPE).stdout.read())

  output = ""
  for _ in range(0, width - 2):
      output += char
  print(output)

#
# Update packages in package manager.
#
def package_update():
  log("Updating package manager...", 0, 1)
  package_manager = detect_package_manager()

  if package_manager == 'apt-get':
    result = os.system('apt-get update -y')
  elif package_manager == 'yum':
    result = os.system('yum check-update -y')
  elif package_manager == 'brew':
    result = os.system('brew update')
  else:
    error("Unknown package manager: " + package_manager)

  if result != 0:
    error("An error occured while updating packages. Fail!")
  else:
    spacer(2)

#
# Install a package through package manager
#
def package(package):
  log("Installing package '%s'..." % package)
  package_manager = detect_package_manager()

  result = test_package_installed(package)

  if result == 0:
    log("Package '%s' is already installed. Skipping." % package)
    return 0

  if package_manager == 'apt-get':
    result = os.system("DEBIAN_FRONTEND=noninteractive apt-get install -y --allow-unauthenticated --allow-downgrades --allow-remove-essential --allow-change-held-packages " + package)
  elif package_manager == 'yum':
    result = os.system("yum install -y " + package)
  elif package_manager == 'brew':
    result = os.system("brew install " + package)
  else:
    error("Unknown package manager: " + package_manager)

  if result != 0:
    error("An error occured while installing package '%s'. Fail!" % package)
  else:
    spacer(2)

#
# Determine if a package is installed or not.
#
# If package is installed, function will return 0. If not, it will return 1.
#
def test_package_installed(package):
  package_manager = detect_package_manager()

  # When many packages are specified, test each.
  if " " not in package:
    packages = [package]
  else:
    packages = package.split(' ')

  result = 0
  if package_manager == 'apt-get':
    for p in packages:
      log("Checking for package '%s'..." % p)
      result += os.system("dpkg-query -l %s | grep -q ^.i" % p)
    return result

  # Don't know how to detect if a package is installed with other package managers.
  return 1

#
# Determine which package manager is in use on the system.
#
def detect_package_manager():
  if command_exist('apt-get'):
    package_manager='apt-get'
  elif command_exist('yum'):
    package_manager='yum'
  elif command_exist('brew'):
    package_manager='brew'
  else:
    error("Could not find a package manager. Fail!")

  log("Detected package manager: " + package_manager)
  return package_manager

#
# Determines if a command exist on the system.
#
def command_exist(cmd):
  return os.system("command -v %s > /dev/null 2>&1;" % cmd) == 0

#
# Copy a file from the assets folder to the specified location.
#
def copy(file, target):
  global DEFAULT_ASSETS_PATH
  global COOKBOOK_ASSETS_PATH
  cookbook_assets_source = COOKBOOK_ASSETS_PATH + "/" + file
  default_assets_source = DEFAULT_ASSETS_PATH + "/" + file

  if os.path.isfile(cookbook_assets_source):
    log("Copying %s to %s..." % (cookbook_assets_source, target))
    shutil.copy(cookbook_assets_source, target)
  elif os.path.isfile(default_assets_source):
    log("Copying %s to %s..." % (default_assets_source, target))
    shutil.copy(default_assets_source, target)
  else:
    error("Could not find '%s' to copy. Fail!" % file)

#
# Add a user to the system.
#
def add_user(user, password=None, no_home=False):

  result = os.system("id %s > /dev/null 2>&1" % user)

  if result == 0:
    log("User %s already exists. Skipped creation." % user)
  else:
    log("Adding user %s..." % user)

    if password is None:
      password = generate_password()

    if no_home:
      os.system("/usr/sbin/useradd --password `openssl passwd -crypt %s` --create-home %s --shell /bin/bash" % (password, user))
    else:
      os.system("/usr/sbin/useradd --password `openssl passwd -crypt %s` %s --shell /bin/bash" % (password, user))

#
# Generate a random password.
#
def generate_password(length=8):
  return ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(length))

#
# Change working directory
#
def cd(loc):
  os.chdir(loc)

#
# Check if file exists.
#
def file_exists(filepath):
  return os.path.isfile(filepath)

#
# Run a shell command
#
def run(cmd):
  log("Running command...")
  log(cmd)
  os.system(cmd)

#
# Run a command as another user
#
def run_as(user, cmd):
  log("Running command as '%s'..." % user)
  log(cmd)
  # sudo -u $user -H -s /bin/bash -c "$cmd"
  # sudo -u $user -s /bin/bash -i "$cmd"
  os.system('su -c "%s" -s /bin/bash %s' % (cmd, user))

#
# Add line to a file if line is not already present
#
def add_line(line, f):
  result = os.system("grep \"%s\" %s > /dev/null 2>&1" % (line, f))

  if result != 0:
    log("Adding '%s' to '%s'..." % (line, f))
    os.system('echo "%s" >> %s' % (line, f))
  else:
    log("'%s' already in '%s'. Skipping." % (line, f))

#
# Write a warning if user is not root.
#
def warn_if_not_root():
  if os.getuid() != 0:
    print("WARNING: You are NOT running this script as 'root'. You might want to consider that...")

#
# Stops the execution of the script if user is not root.
#
def fail_if_not_root():
  if os.getuid() != 0:
    print("You must run this as 'root'. Exiting.")
    sys.exit(1)

#
# Checks if a certain element has already been installed.
#
def is_installed(name):
  name = name.replace(' ', '-')
  name = name.replace('/', '-')
  name = name.replace('\\', '-')
  name = name.replace(':', '-')
  name = name.replace('@', '-')

  if os.path.isfile(os.path.expanduser('~/.shoestrap/installed/') + name):
    log("'%s' is already installed." % name)
    return True
  else:
    log("'%s' is not installed." % name)
    return False

#
# Sets an element as installed.
#
def set_installed(name):
  name = name.replace(' ', '-')
  name = name.replace('/', '-')
  name = name.replace('\\', '-')
  name = name.replace(':', '-')
  name = name.replace('@', '-')

  os.system("mkdir -p ~/.shoestrap/installed")
  os.system("touch ~/.shoestrap/installed/" + name)



