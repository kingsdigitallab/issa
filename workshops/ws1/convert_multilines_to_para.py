p = [
    "This video contains one or more TV programs.",
    "Programs are separated by a special, full-screen visual separator.",
    "A visual separator usually looks like color bars, blank screen or white noise.",
    "The visual separators are not meant for public audience, only for production team.",
    "A separator may last between a second to a few minutes.",
    "They are very distinct from title screens or anything else within a program.",
    "Usually separators in a video will look like each other.",
    "",
    "Spot all separators in the video.",
    "Then responds only with a valid JSON array of programs with `start` and `end` timecodes (format is 'HH:MM:SS').",
    "Here is an example of a response for two detected programs:",
    "```json",
    "[",
    "    {",
    "        \"start\": \"00:01:14\",",
    "        \"end\": \"00:06:23\"",
    "    },",
    "    {",
    "        \"start\": \"00:10:45\",",
    "        \"end\": \"00:24:32\"",
    "    }",
    "]",
    "```"
]

print('\n'.join(p))
