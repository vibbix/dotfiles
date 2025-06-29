Import-Module DisplayConfig
Import-Clixml $home\OfficeSetup.xml | Use-DisplayConfig -UpdateAdapterIds