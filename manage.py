#!/usr/bin/env python3
import os
import sys

def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "playlistor.dev_settings")
    from django.core.management import execute_from_command_line
    from django.core.management.base import CommandError
    try:
        execute_from_command_line(sys.argv)
    except CommandError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
   main() 
