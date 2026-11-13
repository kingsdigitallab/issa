# AI attribution

Any newly written source code file (e.g. .js, .py, .md) 
should contain a comment at the top that says:
File created by AI Assistant ASSISTANT_NAME (MODEL_NAME), 
prompted by GITHUBID, with prompt "PROMPT_SUMMARY"

The PROMPT_SUMMARY keeps it short and leave out any sensitive information.

# Workshops

Any code or data file that is custom to a specific workshop should live
somewhere under `workshops/wsX` where X is the workshop number. 
`workshops/wsX/batches` contains read-only FrameSense output.
`workshops/wsX/catalogue` contains high-level input or output metadata about 
the workshop video batches.

It is however encouraged to generalise the code and keep any small script 
reusable across multiple workshops under `workshops/utils`.
Any larger set of related scripts, like `paratext`, which are used across
multiple workshop, should live in its own subfolder under `workshops`.

# Coding style

* Keep the code simple, clean and human readable; no gold-plating
* Keep functions small
* Each script should preferably focus on a single operation
* Avoid code duplication
* Declare constants for hard-coded literals near the top of the script
* Document scripts in README.md
