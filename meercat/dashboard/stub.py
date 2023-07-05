#function defined in Unit folder as stub.
doxygen_stub = '''
!> @copyright Copyright 2022 UChicago Argonne, LLC and contributors
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
!! @brief %%function_name%% stub

!> @ingroup %%unit_name%%
!!
!! @brief %%function_brief%%
!!
!! @details
!! @anchor %%function_name%%_stub
!!
!! %%function_details%%
!!
!! @note %%function_note%%
!!
%%param_breakout%%
'''
#subroutine MoL_registerUpdate(updateType, updateFunc)  for instance


doxygen_implementation = '''
!> @copyright Copyright 2022 UChicago Argonne, LLC and contributors
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
!! @brief %%function_name%% implementation

!> @ingroup %%current_folder%%
!!
!! @brief %%function_brief%%
!!
!! @stubref{%%function_name%%}
'''
#subroutine MoL_registerUpdate(updateType, updateFunc)


#folder_name.dox
unit_dox_file = '''
/**
    @copyright Copyright 2022 UChicago Argonne, LLC and contributors

    @par License
    @parblock
      Licensed under the Apache License, Version 2.0 (the "License");
      you may not use this file except in compliance with the License.

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS,
      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
      See the License for the specific language governing permissions and
      limitations under the License.
    @endparblock
    
    @defgroup %%unit_name%%
    @ingroup %%containing_folder%%
   
    @brief %%unit_brief%%

    @details
    For further information, please refer to @ref %%readme_path%%
*/
'''


#folder_name.dox
intermediate_dox_file = '''
/**
   @copyright Copyright 2022 UChicago Argonne, LLC and contributors

    @par License
    @parblock
      Licensed under the Apache License, Version 2.0 (the "License");
      you may not use this file except in compliance with the License.

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS,
      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
      See the License for the specific language governing permissions and
      limitations under the License.
   @endparblock

   @internal
   @defgroup %%current_folder%% %%current_folder%%
   @ingroup %%containing_folder%%

   @brief %%folder_brief%%
*/
'''