# -*- mode: python -*-

import os

from atcprocessor.version import VERSION_TITLE


block_cipher = None

console_mode = input('Would you like console output? (y/[n])\n').lower().startswith('y')
onefile_mode = input('Would you like onefile mode? (y/[n])\n').lower().startswith('y')

a = Analysis(['gui.py'],
             pathex=[os.getcwd()],
             binaries=[],
             datas=[],
             hiddenimports=['pandas._libs.tslibs.timedeltas', 'pandas._libs.tslibs.np_datetime', 'pandas._libs.tslibs.nattype', 'pandas._libs.skiplist', 'scipy._lib.messagestream'],
             hookspath=[],
             runtime_hooks=[],
             excludes=['PyQt5', 'mkl'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

if onefile_mode:
	exe = EXE(pyz,
			  a.scripts,
			  a.binaries,
			  a.zipfiles,
			  a.datas,
			  name=VERSION_TITLE,
			  debug=False,
			  strip=False,
			  upx=True,
			  runtime_tmpdir=None,
			  console=console_mode )
else:
	exe = EXE(pyz,
			  a.scripts,
			  exclude_binaries=True,
			  name='ATCProcessor',
			  debug=False,
			  strip=False,
			  upx=True,
			  console=console_mode )
	coll = COLLECT(exe,
				   a.binaries,
				   a.zipfiles,
				   a.datas,
				   strip=False,
				   upx=True,
				   name=VERSION_TITLE)
