import unittest
from .utilities import python_doxygen_template, fortran_doxygen_template, c_doxygen_template

class PythonDoxygenTestCase(unittest.TestCase):
    def test_map_range(self):
        # uncomment next line to see output diffrerence in case of assert not equal
        # self.maxDiff = None
        map_range_str = "def map_range(number:int, in_min:list, in_max, out_min:dict, out_max) -> list:"
        map_range_template = (
"""\"\"\"!
    @brief Starts a paragraph that serves as a brief description.
    A brief description ends when a blank line or another sectioning command is encountered.

    @details A longer description.

    @author name

    @callgraph
    
    @param number [int] Description of parameter.
    @param in_min [list] Description of parameter.
    @param in_max [-] Description of parameter.
    @param out_min [dict] Description of parameter.
    @param out_max [-] Description of parameter.

    @return [list] Description of returned value.
\"\"\"""")
        self.assertEqual(python_doxygen_template(map_range_str), map_range_template)

class FortranDoxygenTestCase(unittest.TestCase):

    def test_map_range(self):
        # uncomment next line to see output diffrerence in case of assert not equal
        # self.maxDiff = None
        fortran_subroutine = (
            """subroutine gr_markRefineDerefineCallback(lev, &
                                                        tags, &
                                                        time, &
                                                        tagval, &
                                                        clearval) bind(c)
                use iso_c_binding, ONLY : C_CHAR, &
                                            C_PTR

                use milhoja_types_mod, ONLY : MILHOJA_INT, &
                                                MILHOJA_REAL

                implicit none

                integer(MILHOJA_INT), intent(IN), value :: lev
                type(C_PTR),          intent(IN), value :: tags
                real(MILHOJA_REAL),   intent(IN), value :: time
                character(C_CHAR),    intent(IN), value :: tagval    
                character(C_CHAR),    intent(IN), value :: clearval

                subroutine foo(time)
                    integer :: time
                    ..

                end subroutine foo
                    
                    RETURN
                !   write(*,'(A)') "[gr_markRefineDerefineCallback] AMReX wants marking"
                end subroutine gr_markRefineDerefineCallback
                """)

        fortran_template = (
"""
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
!! @param lev Descirption
!! @param tags Descirption
!! @param time Descirption
!! @param tagval Descirption
!! @param clearval Descirption
!!
""")
        self.assertEqual(fortran_doxygen_template(fortran_subroutine), fortran_template)

class CDoxygenTestCase(unittest.TestCase):

    def test_c_doxygen_template(self):
        c_function_header = "void my_func(int a, char b, char c, cstmType my_Type, cstmPtr ***pointer)"
        c_template = """/**
  * @params a b c my_Type pointer
  *
  **/
"""

        self.assertEqual(c_doxygen_template(c_function_header), c_template)