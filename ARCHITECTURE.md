# System architecture

* business - captures business entities and basic functions for querying them.

* db - serialize business entities to JSON and back (relies on Business)
* crawler - allows loading of business entities from Katastr nemovitostí (relies on DB, Business)
* reports.presence - Prints a html document with currently present people.
* reports.handsignatures - Prints a html document for hand signing for presence.
* reports.voting - Prints details about all votings.
* inputs - defines interface for interactive CLI
* console - implements input interface for console depends on inputs
* actions.add_person - Depends on Business and Inputs - defines fine grained function for adding
* actions.remove_person - Depends on Business and Inputs
* __main__ - contains argument parser to call all above
