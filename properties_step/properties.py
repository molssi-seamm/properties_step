# -*- coding: utf-8 -*-

"""Non-graphical part of the Properties step in a SEAMM flowchart
"""

import fnmatch
import logging
from pathlib import Path
import pkg_resources
import pprint  # noqa: F401

import numpy as np
import pandas

import properties_step
import molsystem
import seamm
from seamm_util import ureg, Q_  # noqa: F401
import seamm_util.printing as printing
from seamm_util.printing import FormattedText as __

# In addition to the normal logger, two logger-like printing facilities are
# defined: "job" and "printer". "job" send output to the main job.out file for
# the job, and should be used very sparingly, typically to echo what this step
# will do in the initial summary of the job.
#
# "printer" sends output to the file "step.out" in this steps working
# directory, and is used for all normal output from this step.

logger = logging.getLogger(__name__)
job = printing.getPrinter()
printer = printing.getPrinter("Properties")

# Add this module's properties to the standard properties
path = Path(pkg_resources.resource_filename(__name__, "data/"))
csv_file = path / "properties.csv"
if path.exists():
    molsystem.add_properties_from_file(csv_file)


class Properties(seamm.Node):
    """
    The non-graphical part of a Properties step in a flowchart.

    Attributes
    ----------
    parser : configargparse.ArgParser
        The parser object.

    options : tuple
        It contains a two item tuple containing the populated namespace and the
        list of remaining argument strings.

    subflowchart : seamm.Flowchart
        A SEAMM Flowchart object that represents a subflowchart, if needed.

    parameters : PropertiesParameters
        The control parameters for Properties.

    See Also
    --------
    TkProperties,
    Properties, PropertiesParameters
    """

    def __init__(
        self, flowchart=None, title="Properties", extension=None, logger=logger
    ):
        """A step for Properties in a SEAMM flowchart.

        You may wish to change the title above, which is the string displayed
        in the box representing the step in the flowchart.

        Parameters
        ----------
        flowchart: seamm.Flowchart
            The non-graphical flowchart that contains this step.

        title: str
            The name displayed in the flowchart.
        extension: None
            Not yet implemented
        logger : Logger = logger
            The logger to use and pass to parent classes

        Returns
        -------
        None
        """
        logger.debug(f"Creating Properties {self}")

        super().__init__(
            flowchart=flowchart,
            title="Properties",
            extension=extension,
            module=__name__,
            logger=logger,
        )  # yapf: disable

        self._metadata = properties_step.metadata
        self.parameters = properties_step.PropertiesParameters()

    @property
    def version(self):
        """The semantic version of this module."""
        return properties_step.__version__

    @property
    def git_revision(self):
        """The git version of this module."""
        return properties_step.__git_revision__

    def description_text(self, P=None):
        """Create the text description of what this step will do.
        The dictionary of control values is passed in as P so that
        the code can test values, etc.

        Parameters
        ----------
        P: dict
            An optional dictionary of the current values of the control
            parameters.
        Returns
        -------
        str
            A description of the current step.
        """
        if not P:
            P = self.parameters.values_to_dict()

        method = P["method"]
        if self.is_expr(method):
            text = (
                "The variable {method} will determine what to do with the properties. "
                "The other parameters are:"
            )
            for key, value in P:
                if key != "method":
                    text.append(f"\n    {key}: {value}")
        elif method == "export to table":
            text = (
                "Exporting properties from {target} to the table {table}. "
                "The {target} names must match {pattern}, and the properties "
                "matching {properties} will be extracted."
            )

        return self.header + "\n" + __(text, **P, indent=4 * " ").__str__()

    def run(self):
        """Run a Properties step.

        Parameters
        ----------
        None

        Returns
        -------
        seamm.Node
            The next node object in the flowchart.
        """
        next_node = super().run(printer)
        # Get the values of the parameters, dereferencing any variables
        P = self.parameters.current_values_to_dict(
            context=seamm.flowchart_variables._data
        )
        for key in ("pattern", "properties"):
            P[key] = P[key].strip("[]").split(",")

        # Print what we are doing
        printer.important(__(self.description_text(P), indent=self.indent))

        directory = Path(self.directory)
        directory.mkdir(parents=True, exist_ok=True)

        # Get the current system and configuration (ignoring the system...)
        # _, configuration = self.get_system_configuration(None)

        text = None
        method = P["method"]
        if method == "export to table":
            text = self.export_to_table(P)
        else:
            raise RuntimeError(f"Cannot handle '{method}' for the properties")

        if text is not None:
            printer.important(__(text, indent=self.indent + 4 * " "))

        # Add other citations here or in the appropriate place in the code.
        # Add the bibtex to data/references.bib, and add a self.reference.cite
        # similar to the above to actually add the citation to the references.

        return next_node

    def analyze(self, indent="", **kwargs):
        """Do any analysis of the output from this step.

        Also print important results to the local step.out file using
        "printer".

        Parameters
        ----------
        indent: str
            An extra indentation for the output
        """
        printer.normal(
            __(
                "This is a placeholder for the results from the Properties step",
                indent=4 * " ",
                wrap=True,
                dedent=False,
            )
        )

    def export_to_table(self, P):
        """Export the selected properties to the table given.

        Parameters
        ----------
        P : dict
            The control parameters
        """
        system_db = self.get_variable("_system_db")
        db_properties = system_db.properties

        # Create the table if needed
        tablename = P["table"]
        if not self.variable_exists(tablename):
            self.set_variable(
                tablename,
                {
                    "type": "pandas",
                    "table": pandas.DataFrame(),
                    "defaults": {},
                    "loop index": False,
                    "current index": 0,
                    "index column": None,
                },
            )
        table_handle = self.get_variable(tablename)
        table = table_handle["table"]

        # Get the properties.
        target_type = P["target"]
        pattern = P["pattern"]
        properties = P["properties"]

        if target_type == "systems":
            targets = system_db.get_systems(pattern)
            if "System" not in table.columns:
                table_handle["defaults"]["System"] = ""
                table["System"] = ""
        else:
            targets = system_db.get_configurations(pattern)
            if "System" not in table.columns:
                table_handle["defaults"]["System"] = ""
                table["System"] = ""
            if "Configuration" not in table.columns:
                table_handle["defaults"]["Configuration"] = ""
                table["Configuration"] = ""

        row_index = table_handle["current index"]
        for target in targets:
            row = {}
            if target_type == "systems":
                row["System"] = target.name
            else:
                row["Configuration"] = target.name
                row["System"] = target.system.name
            for prop, value in target.properties.get().items():
                for tmp in properties:
                    if fnmatch.fnmatch(prop, tmp):
                        units = db_properties.units(prop)
                        column = prop
                        if column not in table.columns:
                            if units is not None:
                                column += f" ({units})"
                        if column not in table.columns:
                            kind = db_properties.type(prop)
                            if isinstance(value, list):
                                kind = "json"
                                default = ""
                            else:
                                if kind == "boolean":
                                    default = False
                                elif kind == "integer":
                                    default = 0
                                elif kind == "float":
                                    default = np.nan
                                else:
                                    default = ""
                            table_handle["defaults"][column] = default
                            table[column] = default
                        row[column] = [value]
                        break
            new_row = pandas.DataFrame.from_dict(row)
            table = pandas.concat([table, new_row], ignore_index=True)
            row_index += 1
        table_handle["table"] = table
        table_handle["current index"] = table.shape[0] - 1

        # Save the table!
        if "filename" not in table_handle:
            path = Path(self.flowchart.root_directory) / (tablename + ".csv")
            table_handle["filename"] = str(path)
        path = Path(table_handle["filename"])
        file_type = path.suffix
        filename = str(path)

        index = table_handle["index column"]
        if file_type == ".csv":
            if index is None:
                table.to_csv(filename, index=False)
            else:
                table.to_csv(filename, index=True, header=True)
        elif file_type == ".json":
            if index is None:
                table.to_json(filename, indent=4, orient="table", index=False)
            else:
                table.to_json(filename, indent=4, orient="table", index=True)
        elif file_type == ".xlsx":
            if index is None:
                table.to_excel(filename, index=False)
            else:
                table.to_excel(filename, index=True)
        elif file_type == ".txt":
            with open(filename, "w") as fd:
                if index is None:
                    fd.write(table.to_string(header=True, index=False))
                else:
                    fd.write(table.to_string(header=True, index=True))

        text = f"Wrote {len(targets)} rows to the table and saved it as {filename}"
        return text
