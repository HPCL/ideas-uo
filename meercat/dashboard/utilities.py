import ast
import mimetypes
import os
import re
import requests
from datetime import datetime
from google.oauth2.credentials import Credentials

# from git import Repo

from django.conf import settings
from database.models import EventLog
from database.utilities import get_repo_owner


def save_debug_event(log, json="", pull_request=None, request=None):
    if request is not None:
        uri = request.build_absolute_uri()
        view_name = request.resolver_match.view_name
        if request.user.is_anonymous:
            user = None
        else:
            user = request.user
    else:
        uri = ""
        view_name = ""
        user = None

    debug_event = EventLog(
        user=user,
        uri=uri,
        view_name=view_name,
        event_type=EventLog.EventTypeChoices.DEBUGGING,
        datetime=datetime.today(),
        log=log,
        json=json,
        pull_request=pull_request,
    )
    debug_event.save()


def get_branches_with_status(project):  # only works with public repos for now
    repo_owner = get_repo_owner(project)
    repo_name = project.name

    pulls_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls?state=all"
    branches_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/branches"

    pulls = requests.get(pulls_url).json()
    branches = requests.get(branches_url).json()

    branch_names = [branch["name"] for branch in branches]
    processed_branches = []
    branches_with_status = []

    # Process branches with pull request
    for pr in pulls:
        branch_name = pr["head"]["ref"]
        if branch_name in branch_names and branch_name not in processed_branches:
            branches_with_status.append({"branch": branch_name, "status": pr["state"]})
            processed_branches.append(branch_name)

    # Process branches without pull request
    for branch_name in branch_names:
        if branch_name not in processed_branches:
            branches_with_status.append(
                {"branch": branch_name, "status": "No Pull Request"}
            )

    return branches_with_status


# Credits to https://stackoverflow.com/a/56469542/7281070
# Edited for project needs
def list_files_in_commit(commit, directory=None):
    """
    Lists files in a repo at a given commit

    Parameters
    ----------
    directory: str, optional
        Directory path relative to git repo. Only files under directory will be listed.
        If directory is None, all files at the given commit are listed.
    """
    file_list = []
    stack = [commit.tree] if directory is None else [commit.tree[directory]]
    while len(stack) > 0:
        tree = stack.pop()
        # enumerate blobs (files) at this level
        for b in tree.blobs:
            file_list.append(b.path)
        for subtree in tree.trees:
            stack.append(subtree)
    return file_list


def list_project_files(project_name, directory=None, branch=None):
    """
    Lists project files tracked by git in the project project_name

    Parameters
    ----------

    directory: str, optional
        Directory path relative to git repo. Only files under directory will be listed.
        If directory is None, all files are listed.
    branch: str, optional
        Specifies from which branch the files are listed. If None, the default branch is chosen.
    """

    project_repo = Repo(settings.REPOS_DIR / project_name).commit(branch)

    return list_files_in_commit(project_repo, directory)


python_doxygen_base_template = """\"\"\"!
    @brief Starts a paragraph that serves as a brief description.
    A brief description ends when a blank line or another sectioning command is encountered.

    @details A longer description.

    @author name

    @callgraph
    
"""

copyright_template = """!> @copyright Copyright 2022 UChicago Argonne, LLC and contributors
!!
!! @licenseblock
!!   Licensed under the Apache License, Version 2.0 (the "License");
!!   you may not use this file except in compliance with the License.
!!
!!   Unless required by applicable law or agreed to in writing, software
!!   distributed under the License is distributed on an "AS IS" BASIS,
!!   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
!!   See the License for the specific language governing permissions and
!!   limitations under the License.
!! @endlicenseblock
!!
!! @file
!! @brief %%function_name%% %%file_type%%
"""

stub_template = """!> @ingroup %%unit_name%%
!!
!! @brief %%function_brief%%
!!
!! @details
!! @anchor %%function_name%%_stub
!!
!! %%function_details%%
!!
!!
%%param_breakout%%
"""

imp_template = """!> @ingroup %%current_folder%%
!!
!! @brief %%function_brief%%
!!
!! @stubref{%%function_name%%}
"""

user_fields = ["%%function_brief%%", "%%function_details%%", "_description%%"]


# check for @copyright at top of file
def missing_doxygen(lines):
    assert isinstance(lines, list)
    for line in lines:
        if line.strip():
            return not line.startswith("!> @copyright")  # True if not Doxygen commented


def number_of_subroutines(lines):
    count = 0
    for i, line in enumerate(lines):
        if line.startswith("subroutine"):
            count += 1
    return count


def find_subroutine(lines):
    assert isinstance(lines, list)

    main = []  # non-comment code up until subroutine
    comments = []  # exsiting robodoc comment lines
    for i, line in enumerate(lines):
        if line.startswith("!!"):
            comments.append(line)
            continue
        if line.startswith("subroutine"):
            sub_start = i
            break
        main.append(line)  # no subroutine yet and not comment
    else:
        assert False, f"did not find subroutine in file"

    name, params = parse_signature(lines, sub_start)

    return comments, main, sub_start, name, params


# deals with multi-line and single line
def parse_signature(lines, i):
    assert isinstance(lines, list)
    assert i < len(lines)
    assert lines[i].startswith("subroutine")
    try:
        j = lines[i].index("(")
    except:
        assert (
            False
        ), f"missing ( in signature {lines[i]}"  # assuming start of params is on first line

    start = i
    # deal with multi line signature
    while not lines[i].strip().endswith(")"):
        i += 1
        assert i < len(lines), f"did not find closing ) for {lines[i]}"
    # found signature end
    line = " ".join(lines[start : i + 1]).replace("&", " ")
    name = line[len("subroutine") + 1 : j].strip()
    params = line[j + 1 : line.find(")")].split(",")

    return name, [p.strip() for p in params]


def build_new_stub_file(
    copyright_dox, stub_dox, lines, main, sub_start, name, params, current_folder
):
    new_file = copyright_dox + "\n".join(main)  # everything up to subroutine
    new_file += stub_dox  # add rest of dox comments
    new_file += "\n".join(lines[sub_start:])
    new_file = new_file.replace("%%file_type%%", "stub")
    new_file = new_file.replace("%%function_name%%", name)
    new_file = new_file.replace("%%unit_name%%", current_folder)

    params_string = ""
    for param in params:
        params_string += f"!! @param {param} %%{param}_description%%\n"
    new_file = new_file.replace("%%param_breakout%%", params_string)

    return new_file  # as string


def build_new_imp_file(
    copyright_dox, imp_dox, lines, main, sub_start, name, current_folder
):
    new_file = copyright_dox + "\n".join(main)  # everything up to subroutine
    new_file += imp_dox  # add rest of dox comments
    new_file += "\n".join(lines[sub_start:])
    new_file = new_file.replace("%%file_type%%", "implementation")
    new_file = new_file.replace("%%function_name%%", name)
    new_file = new_file.replace("%%current_folder%%", current_folder)

    return new_file  # as string


def find_fields_to_fill(lines, user_fields):
    to_fill = []
    for i, line in enumerate(lines):
        for field in user_fields:
            if field in line:
                to_fill.append((i, field))
    return to_fill


# making lines global for now - normally would be generated by read
def dox_script(path_location, file_path):
    new_file = ""
    comments = ""

    file_parts = Path(file_path).parts

    if len(file_parts) < 2:
        print(f"{file_path} not part of a Unit. Nothing done.")
        return new_file, f"{file_path} not part of a Unit. Nothing done."

    current_folder = file_parts[-2]

    if (
        file_parts[0] != "source" or not file_parts[1][0].isupper()
    ):  # all Unit folders start upper case
        print(f"{file_path} not part of a Unit. Nothing done.")
        return new_file, f"{file_path} not part of a Unit. Nothing done."

    unit = file_parts[1]

    file_type = "stub" if len(file_parts) == 3 else "imp"
    the_file = file_parts[-1]
    filename, extension = os.path.splitext(the_file)

    if extension != ".F90":
        print(f"{file_path} not an F90 file. Nothing done.")
        return new_file, f"{file_path} not an F90 file. Nothing done."

    if not filename.startswith(unit):
        print(f"{file_name} not public. Nothing done.")
        return new_file, f"{file_name} not public. Nothing done."

    # read the file next
    try:
        with open(f"{path_location}/{file_path}", "r") as f:
            lines = f.readlines()
            f.close()
    except:
        assert False, f"Could not read {file_path}"

    if not lines:
        assert False, f"{filename} is empty"

    if not missing_doxygen(lines):
        to_fill = find_fields_to_fill(lines, user_fields)
        if to_fill:
            print(
                f"{filename} appears to have have Doxygen comments but missing field fillers at these lines: {to_fill}. Nothing done."
            )
            return (
                new_file,
                f"{filename} appears to have have Doxygen comments but missing field fillers at these lines: {to_fill}. Nothing done.",
            )
        else:
            print(
                f"{filename} appears to have no missing Doxygen comments. Nothing done."
            )
            return (
                new_file,
                f"{filename} appears to have no missing Doxygen comments. Nothing done.",
            )

    if number_of_subroutines(lines) != 1:
        print(
            f"{filename} appears to have {number_of_subroutines(lines)} subroutines. Can only handle 1 currently. Nothing done."
        )
        return (
            new_file,
            f"{filename} appears to have {number_of_subroutines(lines)} subroutines. Can only handle 1 currently. Nothing done.",
        )

    if file_type == "stub":
        comments, main, sub_start, name, params = find_subroutine(lines)
        new_file = build_new_stub_file(
            copyright_template,
            stub_template,
            lines,
            main,
            sub_start,
            name,
            params,
            current_folder,
        )
    elif file_type == "imp":
        comments, main, sub_start, name, params = find_subroutine(lines)
        new_file = build_new_imp_file(
            copyright_template,
            imp_template,
            lines,
            main,
            sub_start,
            name,
            current_folder,
        )
    else:
        assert False, f"Not imp or stub."

    return new_file, "\n".join(comments)  # both strings


def get_type_hints(tree):
    arguments = []
    return_type = ""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for argument in node.args.args:
                arguments.append(
                    {
                        "name": argument.arg,
                        "type": argument.annotation.id if argument.annotation else "-",
                    }
                )
            return_type = node.returns.id if node.returns else "-"

    return arguments, return_type


def python_doxygen_template(function_definition):
    pass_str = " pass" if function_definition[-1] == ":" else ": pass"
    tree = ast.parse(function_definition + pass_str, type_comments=True)
    arguments, return_type = get_type_hints(tree)
    template = python_doxygen_base_template

    for argument in arguments:
        template += f"    @param {argument['name']} [{argument['type']}] Description of parameter.\n"

    template += f'\n    @return [{return_type}] Description of returned value.\n"""'

    return template


fortran_doxygen_base_template = """
!> @copyright Copyright 2022 UChicago Argonne, LLC and contributors
!!
!! @licenseblock
!! Licensed under the Apache License, Version 2.0 (the "License");
!! you may not use this file except in compliance with the License.
!!
!! Unless required by applicable law or agreed to in writing, software
!! distributed under the License is distributed on an "AS IS" BASIS,
!! WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
!! See the License for the specific language governing permissions and
!! limitations under the License.
!! @endlicenseblock
!!
!! @brief brief description.
!!
!! @details longer description
!!
"""


def get_fortran_parameters(subroutine: str) -> list:
    params = []
    m = re.match(
        "subroutine (?P<subroutine>[a-zA-Z]\w{0,30})\((?P<params>[\s\S]*?)\)",
        subroutine,
    )
    for param in m.group("params").split(","):
        param = param.replace("&", "")
        params.append(param.strip())

    return params


def fortran_doxygen_template(subroutine):
    template = fortran_doxygen_base_template
    parameters = get_fortran_parameters(subroutine)

    for parameter in parameters:
        template += f"!! @param {parameter} Descirption\n"

    template += "!!\n"
    return template


c_doxygen_base_template = """/**
  * @params """


def get_c_parameters(subroutine: str) -> list:
    params = []
    m = re.search(
        "(?P<subroutine>[a-zA-Z]\w{0,30})\((?P<params>[\s\S]*?)\)", subroutine
    )
    for param in m.group("params").split(","):
        param = param.replace("*", "")
        params.append(param.strip().split()[1])

    return params


def c_doxygen_template(c_function_header):
    template = c_doxygen_base_template
    parameters = get_c_parameters(c_function_header)

    template += " ".join(parameters)
    template += "\n  *\n  **/\n"

    return template


from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.message import EmailMessage
import base64

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.metadata",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def gmail_send_message(
    subject,
    body,
    image=None,
    sender="uomeercat@gmail.com",
    recipient_list=["uomeercat@gmail.com"],
):
    """Create and send an email message
    Print the returned  message id
    Returns: Message object, including message id

    Load pre-authorized user credentials from the environment.
    TODO(developer) - See https://developers.google.com/identity
    for guides on implementing OAuth2 for the application.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(settings.BASE_DIR / "token.json"):
        creds = Credentials.from_authorized_user_file(
            settings.BASE_DIR / "token.json", SCOPES
        )
    else:
        raise Exception("Token file not found")

    if not creds or not creds.valid:
        print("Creds not valid, will try to refresh creds")
        if creds and creds.expired and creds.refresh_token:
            print("Expired creds found with refresh token")
            creds.refresh(Request())
        else:
            raise Exception("Token could not be refreshed")
        # Save the credentials for the next run
        with open(settings.BASE_DIR / "token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("gmail", "v1", credentials=creds)
        message = EmailMessage()

        message["To"] = ", ".join(recipient_list)
        message["From"] = sender
        message["Subject"] = subject

        message.set_content(body)

        if image is not None:
            # Guessing the MIME type
            type_subtype, _ = mimetypes.guess_type(image.name)
            maintype, subtype = type_subtype.split("/")

            image_content = image.read()
            message.add_attachment(image_content, maintype, subtype)

        # encoded message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        create_message = {"raw": encoded_message}
        send_message = (
            service.users().messages().send(userId="me", body=create_message).execute()
        )

        # Save email event
        email_event = EventLog(
            event_type=EventLog.EventTypeChoices.EMAIL,
            datetime=datetime.today(),
            log=str(message),
        )
        email_event.save()
        print(f'Message Id: {send_message["id"]}')
    except HttpError as error:
        print(f"An error occurred: {error}")

        # Save failed email event
        failed_email_event = EventLog(
            event_type=EventLog.EventTypeChoices.EMAIL_FAIL,
            datetime=datetime.today(),
            log=str(error),
        )
        failed_email_event.save()

        send_message = None

    return send_message


if __name__ == "__main__":
    gmail_send_message(
        subject="This is an email test", body="Kindly ignore this message"
    )
