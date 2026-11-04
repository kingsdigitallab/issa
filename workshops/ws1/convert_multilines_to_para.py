p = [
    "The attached video is a single programme from a very diverse collection at a national screen archive.",
    "Sometimes a professional programme can contain raw unedited rushes with outtakes or retakes.", 
    "Returns a valid JSON dictionary with the following keys:",
    "* programme ('true' if this is an actual programme with meaningful content that can be broadcast; 'false' if this is mostly visual markers like blank screen, color bars, white noise),",
    "* bands (a list of music bands featuring in this programme, for each one its `name` and a list of `activities` such as 'music video', 'studio performance', 'concert performance', 'interview', 'other'; [] if no band in the programme),",
    "* environment (in two words maximum, the primary type of environment the programme takes place in, such as `forest`, `street`, `studio`, `school`)"
]

print('\n'.join(p))
