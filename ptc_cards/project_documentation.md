[metadata:tags]:- "bssw-psip-ptc"
# Structured Project Documentation with MeerCat support

<a href='download.png' width='18'> Download this PTC (Markdown)</a>

## Target

Improve our team’s project documentation. This includes code documentation and user documentation. Lessen burden on code reviewers to hunt for missing documentation.

## Approach

Use documentation structuring tools (e.g., Doxygen) that take structured code documentation and produce user-level project documentation, e.g., user manuals in html. Use MeerCat to find missing or erroneous documentation, giving the developer the chance to create it or correct it.


## User Story

* **As a** developer, **I want** to document my code, **so that** it is easy understand and potentially change.
* **As a** user of the software, **I want** to know what functionality is available to me and how to use it.
* **As a** code reviewer (a Pull-Request reviewer), **I want** to avoid the tedium of searching through files looking for missing or erroneous documentation.


## Card(s)

| Stage         | Description |
| :-------------: | :------------- |
| 0 | Team does ad-hoc code documentation, possibly with a vague mandate to document well. Up to each developer to decide what code to document (possibly none) and how to document. At best, inline comments are scattered through code. User manuals, if they exist, are hand-created.|
| 1 | Team chooses a modern structured-documentation tool, e.g., Doxygen. Developers are required to use Doxygen comments for every major component in their code, e.g., functions, subroutines, structs, classes. Team uses the full-featured structuring features of the tool. A good example are the notion of predefined tags/fields like @param for describing each parameter of a function or @brief for a brief description of a component.  Auto-generated user manuals now become available. <sup>1,2</sup>|
| 2 | Team uses MeerCat to incrementally fill in field content during the Pull Request process, taking some of the burden off of PR reviewers. MeerCat can check for placeholders <sup>2</sup> indicating missing documentation content, and help the developer (PR author) fill them in.|

Eventually, fully-realized structured-documentation is produced and a rich user manual is generated.|


## Comments
1. Aligning what the tool supports in terms of documentation structuring with the Team's documentation goals is a worthwhile but time-intensive effort. Using Doxygen as an example, it has over 100 different fields that can be used. Asking developers to fill in 100 different fields for every component of the system is not reasonable. But choosing which subset to use takes thought on the overall documentation goals of the Team.
2. Using tool support to start the transition to structured-documentation is often feasible. For instance, formatted documentation templates can be inserted at appropriate locations with placeholders for actual content for a developer to fill in.



### Acknowledgement

This Project Tracking Card originated from the [PSIP PTC Catalog](https://bssw-psip.github.io/ptc-catalog/). The development of the PSIP PTC Catalog was supported by the Exascale Computing Project (17-SC-20-SC), a collaborative effort of the U.S. Department of Energy Office of Science and the National Nuclear Security Administration.
