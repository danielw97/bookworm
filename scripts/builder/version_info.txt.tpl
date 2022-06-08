# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    # filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
    # Set not needed items to zero 0.
    filevers=({{ app_version_tuple }}),
    prodvers=({{ app_version_tuple }}),
    # Contains a bitmask that specifies the valid bits 'flags'r
    mask=0x3f,
    # Contains a bitmask that specifies the Boolean attributes of the file.
    flags=0x0,
    # The operating system for which this file was designed.
    # 0x4 - NT and there is no need to change it.
    OS=0x40004,
    # The general type of file.
    # 0x1 - the file is an application.
    fileType=0x1,
    # The function of the file.
    # 0x0 - the function is not defined for this fileType
    subtype=0x0,
    # Creation date and time stamp.
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'{{ app_author }}'),
        StringStruct(u'FileDescription', u'{{ app_name}}: {{ app_description }}'),
        StringStruct(u'FileVersion', u'{{ app_version }}'),
        StringStruct(u'LegalCopyright', u'{{ app_copyright }}'),
        StringStruct(u'OriginalFilename', u'{{ app_name }}.exe'),
        StringStruct(u'ProductName', u'{{ app_name }}'),
        StringStruct(u'ProductVersion', u'{{ app_version }}')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
