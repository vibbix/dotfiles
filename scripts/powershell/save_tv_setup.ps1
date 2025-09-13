#Requires -Modules @{ ModuleName="DisplayConfig"; ModuleVersion="1.0.4" }\
Get-DisplayConfig | Export-Clixml $home\TVGamingProfile.xml