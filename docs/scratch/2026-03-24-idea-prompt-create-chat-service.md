# Chat Service Prompt Guidelines

## Prerequisites

- /services/config_service
- /services/logging_service
- /services/error_service

### Prequiste Specification

- minimal setup needed. application will evolve over time through iteration.
- when displaying errors to users follow best practices and do not show stack trace in production to users, only developers
- each service should be its own module, capable of running on its own, but able to use (import if exists) other services
- no values that can be in env files should be hard coded in the files, always use environment variables when necessary.
- logs should go to console intially with scalability to move to printed logs, database logs, etc in the future iterations.
- user feed in console log should follow best practices and be verbose whenever possible. 
- color coded feedback

## Chat Service
**Execute plan after prerequisistes are completed.


### Always Follow During Development
- create new issue according to convention
- create new branch off main using the naming convention in tbe previous issues
- use git conventional commits
- use PR best practices
- follow PEP 8 - https://peps.python.org/pep-0008/
- consult contxt7.com using mcp for PEP 8 https://context7.com/websites/peps_python/llms.txt?tokens=10000
- document well, including overview, tldr, developer view, and readme markdown docs for the features