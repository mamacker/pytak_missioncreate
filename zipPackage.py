import os
import shutil
import xml.etree.ElementTree as ET
import uuid
import magic
import zipfile

# Directories/files
ATTACHMENTS_DIR = 'attachments'
PACKAGES_DIR = 'packages'
ZIPS_DIR = 'zips'
PACKAGE_FILE_NAME = 'package.zip'

# Arbitrary manifest parameters
MANIFEST_NAME = 'Manifest Name'

def zipPackage(uid, callsign):
    assert uid != 'MANIFEST'

    attachment_dir = os.path.join(ATTACHMENTS_DIR, uid)
    print("Getting attachments in: " + attachment_dir)

    if os.path.isdir(attachment_dir):
        # Clean package dir
        if os.path.isdir(PACKAGES_DIR):
            shutil.rmtree(PACKAGES_DIR)

        os.makedirs(PACKAGES_DIR)

        # Function to recursively copy files and maintain directory structure
        def recursive_copy(src, dst):
            attachment_files = []
            for item in os.listdir(src):
                s = os.path.join(src, item)
                print("Copying: " + s)
                d = os.path.join(dst, item)
                print("To: " + d)
                if os.path.isdir(s):
                    if not os.path.isdir(d):
                        print("Making dir: " + d)
                        os.makedirs(d)
                        print(f"Taget path exists: {os.path.isdir(d)}")
                    attachment_files.extend(recursive_copy(s, d))
                else:
                    shutil.copy2(s, d)
                    attachment_files.append(os.path.relpath(d, PACKAGES_DIR))
            return attachment_files

        # Copy attachments recursively and get list of files
        package_attachment_dir = os.path.join(PACKAGES_DIR, uid)
        os.makedirs(package_attachment_dir)
        attachment_files = recursive_copy(attachment_dir, package_attachment_dir)

        # Write manifest
        manifest_dir = os.path.join(package_attachment_dir, 'MANIFEST')
        os.makedirs(manifest_dir)
        manifest_path = os.path.join(manifest_dir, 'manifest.xml')
        manifest_text = composeManifest(uid, callsign, attachment_files)
        with open(manifest_path, 'wb') as manifest_file:
            manifest_file.write(manifest_text)
        print("Writing manifest: " + manifest_path)
        attachment_files.append(os.path.relpath(manifest_path, PACKAGES_DIR))

        print(f"Attachment files: {attachment_files}")

        # Clean destination dir
        zip_dst_dir = os.path.join(ZIPS_DIR, uid)
        if os.path.isdir(zip_dst_dir):
            shutil.rmtree(zip_dst_dir)
        os.makedirs(zip_dst_dir)

        # Zip file
        zip_dst_path = os.path.join(zip_dst_dir, PACKAGE_FILE_NAME)
        with zipfile.ZipFile(zip_dst_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file in attachment_files:
                print(f"Adding {file} to zip from {os.path.join(PACKAGES_DIR, file)}")
                zip_file.write(os.path.join(PACKAGES_DIR, file), os.path.relpath(file, uid))

        return zip_dst_path

    else:
        print(f"WARNING: No attachments for {uid}")


def composeManifest(uid, callsign, attachment_files):
    mpm = ET.Element('MissionPackageManifest')
    mpm.set('version', '2')

    config = ET.SubElement(mpm, 'Configuration')
    config_uid = ET.SubElement(config, 'Parameter')
    config_uid.set('name', 'uid')
    config_uid.set('value', uid)
    config_name = ET.SubElement(config, 'Parameter')
    config_name.set('name', 'name')
    config_name.set('value', uid+"_name")
    config_del = ET.SubElement(config, 'Parameter')
    config_del.set('name', 'onReceiveDelete')
    config_del.set('value', 'true')
    config_import = ET.SubElement(config, 'Parameter')
    config_import.set('name', 'onReceiveImport')
    config_import.set('value', 'true')
    #Add callsign or group?
    config_callsign = ET.SubElement(config, 'Parameter')
    config_callsign.set('name', 'callsign')
    config_callsign.set('value', callsign)


    contents = ET.SubElement(mpm, 'Contents')
    for file in attachment_files:
        #file_path = os.path.join(PACKAGES_DIR, uid, file)
        local_path = os.path.relpath(file, uid)
        content = ET.SubElement(contents, 'Content')
        content.set('ignore', 'false')
        content.set('zipEntry', local_path)
        content_uid = ET.SubElement(content, 'Parameter') # TODO: Double check this is necessary
        content_uid.set('name', 'uid')
        content_uid.set('value', uid)
        content_iscot = ET.SubElement(content, 'Parameter') # Marks as attachment
        content_iscot.set('name', 'isCoT')
        if (file.endswith('.cot')):
            content_iscot.set('value', 'true')
        else:
            content_iscot.set('value', 'false')
            mime_type = magic.Magic(mime=True).from_file(os.path.join(PACKAGES_DIR,file))
            content_mime = ET.SubElement(content, 'Parameter') # Mime type
            content_mime.set('name', 'contentType')
            content_mime.set('value', mime_type)

    # create a new XML file with the results
    return ET.tostring(mpm)
