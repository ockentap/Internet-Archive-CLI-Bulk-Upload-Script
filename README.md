# Internet Archive CLI Bulk-Upload Script

Since there is no bulk uploading option in the ia tool I made this script, it will make a tedious process easy and automatic if you choose to create a standalone script.
This script uses your ia configuration that is stored in ~/.configure/internetarchive so you will have to login with the regular ia command before you can start using this script.
The script also keeps a sqlite database with identifiers, paths and keeps track of files that are already uploaded so that it doesnt need to run MD5 hash everytime you start the script.




How to use
1. Install Internet Archive CLI

Due to dependenice of the script this must be done via pip or python, you could also install it via other means as long as you have the pip or python version.


Run 

[Agnostic]
  pip install internetarchive
  pip install tqdm

or

[Debian]
  sudo apt install python3-internetarchive
  sudo apt install python3-tqdm

2. Configure ia-cli

Run 

  ia configure 

and enter your login and password.

3. You can now run the python script

  python3 bulk-upload.py

4. Provide information
Type the name of the identifier, if you have uploaded the identifier before it will show up in the list otherwise press 0 to type in a name.
You will be asked for the location, if you have typed a location before it will be show again, you can just press enter if it is correct.
You will be asked to save the script as a standalone, this means that the script can be run without user input via the python3 command,
this is useful if you want to have a folder into which you are constantly adding files be auto uploaded by for instance adding the script to your corntab.

After the script is done it will check the MD5 hash between the uploaded files and the local files, this is very slow and you can exit with Ctrl+C if this is not of interest to you.
