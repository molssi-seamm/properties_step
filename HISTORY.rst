=======
History
=======
2026.10.3 -- Tables in the job's database; property values exported
    * Exports to tables kept in the job's database (seamm 2026.10.3).
    * Bugfix: the table held each property as a record (system, configuration and
      value) instead of its value.
    * Integer properties now become integer columns rather than text.
2026.3.1 -- Internal: switching from deprecated library pkg_resources to importlib

2023.7.31 -- Bugfix: random error creating the tables of properties.

2023.7.30 -- Initial release
    * Initial version, which can export the properties in the database to a table.
