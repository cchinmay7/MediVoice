import os
import zipfile

root = 'lambda_backend_package'
zip_path = 'backend_lambda.zip'

if os.path.exists(zip_path):
    os.remove(zip_path)

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            full_path = os.path.join(dirpath, filename)
            arcname = os.path.relpath(full_path, root)
            zf.write(full_path, arcname)

print('created', zip_path, os.path.getsize(zip_path))
