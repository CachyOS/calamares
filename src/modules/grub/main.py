#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# === This file is part of Calamares - <https://calamares.io> ===
#
#   SPDX-FileCopyrightText: 2014-2021 Anke Boersma <demm@kaosx.us>
#   SPDX-FileCopyrightText: 2014, Benjamin Vaudour <benjamin.vaudour@yahoo.fr>
#   SPDX-License-Identifier: GPL-3.0-or-later
#
#   Calamares is Free Software: see the License-Identifier above.
#

import libcalamares

import os
import subprocess

from libcalamares.utils import check_target_env_call


def detect_firmware_type():
    # Check for EFI variables support
    if(os.path.exists("/sys/firmware/efi/efivars")):
        fw_type = 'efi'
    else:
        fw_type = 'bios'

    libcalamares.globalstorage.insert("firmwareType", fw_type)
    libcalamares.utils.debug("Firmware type: {!s}".format(fw_type))


def get_uuid():
    root_mount_point = libcalamares.globalstorage.value("rootMountPoint")
    print(root_mount_point)
    partitions = libcalamares.globalstorage.value("partitions")
    print(partitions)
    for partition in partitions:
        if partition["mountPoint"] == "/":
            libcalamares.utils.debug(partition["uuid"])
            return partition["uuid"]
    return ""


def install_grub(boot_loader):
    install_path = boot_loader["installPath"]
    check_target_env_call(["grub-install", install_path])
    check_target_env_call(["grub-mkconfig", "-o", "/boot/grub/grub.cfg"])


def run():
    fw_type = libcalamares.globalstorage.value("firmwareType")
    boot_loader = libcalamares.globalstorage.value("bootLoader")
    # Packagechooser@bootchoice outcome
    bootchoice = libcalamares.globalstorage.value("packagechooser_bootchoice")

    if bootchoice != 'grub':
        return None

    if libcalamares.globalstorage.value("bootLoader") is None and fw_type != "efi":
        libcalamares.utils.debug('no bootloader install')
        return None

    install_grub(boot_loader)
    return None
