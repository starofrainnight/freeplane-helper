//
// Installation:
//
// 1. Put this script into {Freeplane User's Directory}/scripts
//
// You could find out the user directory via menu Tools -> Open user directory
//
// 2. Enable folow options via Tools -> Preferences -> Plugins
//
// Script execution enabled: Yes
// All script execution permissions are must checked!
//
// Otherwise script will failed with this error: WARNING: An error occured
// during the script execution: access denied ("
// java.security.SecurityPermission" "getPolicy")
//
// Execute:
//
// After that, you could execute this script by command for example:
//
// freeplane -S -N -XExportToMarkdown_on_selected_node TheFileYouWantToExportFrom.mm
//

def overwriteExistingFile = true;
def filename = './' + node.map.file.name.replaceFirst(/\.mm$/, '.md');
def typeDescriptions = c.getExportTypeDescriptions();

// Find markdown description
for (i = 0; i < c.getExportTypeDescriptions().size(); ++i) {
    typeDesc = typeDescriptions[i];
    if (typeDesc.contains('.markdown')) {
        break;
    }
}

c.statusInfo = typeDesc;

c.export(node.map, new File(filename), typeDesc, overwriteExistingFile);
