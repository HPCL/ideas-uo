!!****if* source/Grid/GridMain/Grid_computeVarMean
!! NOTICE
!!  Copyright 2022 UChicago Argonne, LLC and contributors
!!
!!  Licensed under the Apache License, Version 2.0 (the "License");
!!  you may not use this file except in compliance with the License.
!!
!!  Unless required by applicable law or agreed to in writing, software
!!  distributed under the License is distributed on an "AS IS" BASIS,
!!  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
!!  See the License for the specific language governing permissions and
!!  limitations under the License.
!!
!! NAME
!!
!!  Grid_computeVarMean
!!
!! SYNOPSIS
!!
!!  call Grid_computeVarMean(integer(in) :: iunk,
!!                           real(out) :: mean)
!!
!! DESCRIPTION
!!
!!  Calculates the mean of a variable in UNK
!!
!! ARGUMENTS
!!
!!   iunk : the variable (index into the UNK array)
!!
!!   mean : the mean value returned
!!
!!
!!
!!***

subroutine Grid_computeVarMean(iUnk, mean)
  use gr_interface, ONLY: gr_findMean
  implicit none
  
  integer, intent(in) :: iUnk
  real, intent(out) :: mean

  call gr_findMean(iUnk, iType=2, bGuardCell=.FALSE., mean=mean)

end subroutine Grid_computeVarMean
