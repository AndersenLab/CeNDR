def trim(docstring):
    """trim function from PEP-257"""
    if not docstring:
        return ""
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxsize
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxsize:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)

    # Current code/unittests expects a line return at
    # end of multiline docstrings
    # workaround expected behavior from unittests
    if "\n" in docstring:
        trimmed.append("")

    # Return a single string:
    return "\n".join(trimmed)



def parse_docstring(obj):
    """Parse GoogleDocstring
    """

    short_description = returns = ""
    params = long_description = []
    if hasattr(obj, '__doc__'):
        docstring = obj.__doc__
    elif type(obj) == str:
        docstring = obj
    else:
        raise Exception("Cannot find docstring")
    docstring = trim(docstring)
    lines = list(filter(len,docstring.splitlines()))
    short_description = lines[0]
    for line in lines[1:]:
        if line.endswith(":"):
            break
        long_description.append(line)
    long_description = ' '.join(long_description)

    sections = {}

    # Pull out sections
    for line in lines[1:]:
        if line.endswith(":") and not line.startswith(" "):
            section_title = line[:-1]
        elif line.startswith(" "):
            print(line)








        short_description = lines[0]

        if len(lines) > 1:
            long_description = lines[1].strip()

            params_returns_desc = None

            match = PARAM_OR_RETURNS_REGEX.search(long_description)
            if match:
                long_desc_end = match.start()
                params_returns_desc = long_description[long_desc_end:].strip()
                long_description = long_description[:long_desc_end].rstrip()

            if params_returns_desc:
                params = [
                    {"name": name, "doc": trim(doc)}
                    for name, doc in PARAM_REGEX.findall(params_returns_desc)
                ]

                match = RETURNS_REGEX.search(params_returns_desc)
                if match:
                    returns = reindent(match.group("doc"))

    return {
        "short_description": short_description,
        "long_description": long_description,
        "params": params,
        "returns": returns
    }



def func(arg1, arg2):
    """Summary line.

    Extended description of function.
    with multiple lines
    and more

    Args:
        arg1: Description of arg1
        arg2 (str): Description of arg2

    Returns:
        bool: Description of return value

    """
    return True

