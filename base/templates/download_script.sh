#!/usr/bin/bash

# Use the following line to run this script:
# curl  http://www.elegansvariation.org{{ request.path }} | bash
#
# Requirements:
#    wget is required for downloading files. 
#    We recommend using Homebrew (brew.sh) for Unix/Mac OS or Cygwin (cygwin.com) on windows.
#

{% autoescape off %}
{{script_content}}
{% endautoescape %}
