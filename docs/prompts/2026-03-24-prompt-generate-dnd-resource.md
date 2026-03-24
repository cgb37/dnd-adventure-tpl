# D&D Resource Generator Service Prompt Guidelines

## Directory 

- services/llm_api/src/llm_api/generators/

### Generator Specification

- independent module, self contained
- minimal setup needed. application will evolve over time through iteration.
- when displaying errors to users follow best practices and do not show stack trace in production to users, only developers
- each service should be its own module, capable of running on its own, but able to use (import if exists) other services
- no values that can be in env files should be hard coded in the files, always use environment variables when necessary.
- follow PEP 8
- use existing logging service


## Prerequisites

- /services/llm_api/src/llm_api/services/chat_service.py


### Always Follow During Development
- create new issue according to convention
- create new branch off main using the naming convention in tbe previous issues
- use git conventional commits
- use PR best practices
- use existing config service services/llm_api/src/llm_api/services/config.py
- use existing logging service services/llm_api/src/llm_api/services/logging.py
- use existing error service services/llm_api/src/llm_api/services/errors.py
- follow PEP 8 - https://peps.python.org/pep-0008/
- consult context7.com using mcp for PEP 8 https://context7.com/websites/peps_python/llms.txt?tokens=10000
- document python methods and classes
- document features including overview, tldr, developer view, in README.md markdown docs for the features