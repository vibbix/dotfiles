#Requires -Modules @{ ModuleName="DisplayConfig"; ModuleVersion="1.0.4" }
Import-Module DisplayConfig
Import-Clixml $home\TVGamingProfile.xml | Use-DisplayConfig -UpdateAdapterIds