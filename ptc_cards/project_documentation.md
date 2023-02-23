[metadata:tags]:- "bssw-psip-ptc"
# Structured Project Documentation

<a href='download.png' width='18'> Download this PTC (Markdown)</a>

## Target

Improve our team’s project documentation. This includes code documentation and user documentation.

## Approach

Use documentation structuring tools (e.g., Doxygen) that take structured code documentation and produce user-level project documentation, e.g., user manuals in html.


## User Story

* **As a** developer, **I want** to document my code, **so that** it is easy understand and potentially change.
* **As a** user of the software, **I want** to know what functionality is available to me and how to use it. 


## Card(s)

| Stage         | Description |
| :-------------: | :------------- |
| 0 | Team does ad-hoc code documentation. Up to each developer to decide what code to document (possibly none) and how to document. At best, inline comments are scattered through code. User manuals, if they exist, are hand-created.|
| 1 | Team has a vague mandate to document well. What and how remain ad hoc. User manuals are hand-created.|
| 2 | Team chooses a modern structured-documentation tool, e.g., Doxygen. Developers are required to use Doxygen comments for every major component in their code, e.g., functions, subroutines, structs, classes. Structure of comments remains loose. User manuals are now automatically built from code comments. <sup>1</sup>| 
| 3 | Team uses the often full-featured structuring features of a tool, e.g., Doxygen. A good example are the notion of predefined tags/fields like @param for describing each parameter of a function or @brief for a brief description of a component.  Auto-generated user manuals now become more useful. <sup>2</sup>|
| 4 | Team relies on the PR process to incrementally fill in fields. PR reviewers check for missing field content and ask PR author to fill in.| 
| 5 | Team uses MeerCat to check for placeholders indicating missing content, relieving the reviewer of this task. MeerCat can find fields with missing content and help the developer (PR author) fill them in.|
| 6 | Eventually, fully-realized structured-documentation is produced and a rich user manual is generated. A win for both developers and users.|


## Comments
1. Using tool support to start the transition to structured-documentation is often feasible. For instance, formatted documentation templates can be inserted at appropriate locations with placeholders for actual content for a developer to fill in.
2. Again, tool support to generate the required fields is often possible, leaving the actual content of the field for the developer to fill in.


### Acknowledgement

This Project Tracking Card originated from the [PSIP PTC Catalog](https://bssw-psip.github.io/ptc-catalog/). The development of the PSIP PTC Catalog was supported by the Exascale Computing Project (17-SC-20-SC), a collaborative effort of the U.S. Department of Energy Office of Science and the National Nuclear Security Administration.
