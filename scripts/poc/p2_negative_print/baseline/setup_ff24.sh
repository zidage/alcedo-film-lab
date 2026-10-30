#!/bin/bash
# Runs as root inside the imported Ubuntu 24.04 distro: packages for the Fotufilm engine and the local driver.
set -u
export DEBIAN_FRONTEND=noninteractive
mkdir -p /opt
if [ ! -d /opt/squashfs-root ]; then
  cd /opt && cp "/mnt/d/Projects/alcedo-film-lab/build/tmp/baseline/dl_fotufilm/Fotufilm-Linux-x86_64.AppImage" app.AppImage
  chmod +x app.AppImage
  apt-get -qq update
  apt-get -qq -y install --no-install-recommends squashfs-tools python3 python3-numpy python3-pil libtiff6 libsharpyuv0 libwebp7 libgomp1 libvulkan1 libgl1 libegl1 libglib2.0-0t64 >/dev/null
  offset=$(./app.AppImage --appimage-offset 2>/dev/null || true)
  if [ -z "$offset" ]; then
    # type 2 AppImage: find the squashfs magic after the ELF runtime
    offset=$(LC_ALL=C grep -abo 'hsqs' app.AppImage | head -1 | cut -d: -f1)
  fi
  unsquashfs -q -o "$offset" -d squashfs-root app.AppImage >/dev/null
fi
cd /opt/squashfs-root/usr/lib/fotufilm/lib
LD_LIBRARY_PATH=.:/usr/lib/wsl/lib ldd libfotufilm.so | grep -i 'not found'
echo "ldd done"
ls /usr/lib/wsl/lib | grep -c cuda
ls /dev/dxg
