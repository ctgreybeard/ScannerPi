##Formatters

This package (directory) contains formatters for scanner (BCDX96XT) responses.

Each formatter is named by the command that generated the response. This is determined by taking the
first 'word' of the response, in upper case as it appears, as the module name.

###Requirements

Each module **MAY** supply the following:

*decode(response)* **OR** *varlist*

*decode* is a function that populates the *val* dict in *response*

*varlist* is an ordered list or tuple of the names to be applied to the parts of the response.

If *decode* is not supplied a generic decode will be used against *varlist*, this is usually sufficient.

If neither are supplied a generic *decode* will be applied against a generic *varlist*

The module **MAY** supply a *display* function which returns a string formatted from *response*

*varlist* **includes** the command and is usually named 'CMD' (but this is simply convention)
