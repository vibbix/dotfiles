#Requires -Modules @{ ModuleName="DisplayConfig"; ModuleVersion="1.0.4" }
Import-Module DisplayConfig
Import-Clixml $home\OfficeSetup.xml | Use-DisplayConfig -UpdateAdapterIds