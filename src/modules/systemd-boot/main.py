#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# === This file is part of Calamares - <https://calamares.io> ===
#
#   SPDX-FileCopyrightText: 2014-2021 Anke Boersma <demm@kaosx.us>
#   SPDX-FileCopyrightText: 2014 Benjamin Vaudour <benjamin.vaudour@yahoo.fr>
#   SPDX-FileCopyrightText: 2017 Gabriel Craciunescu <crazy@frugalware.org>
#   SPDX-License-Identifier: GPL-3.0-or-later
#
#   Calamares is Free Software: see the License-Identifier above.
#

import libcalamares

import os
import subprocess

from libcalamares.utils import check_target_env_call

import gettext
_ = gettext.translation("calamares-python",
                        localedir=libcalamares.utils.gettext_path(),
                        languages=libcalamares.utils.gettext_languages(),
                        fallback=True).gettext


def pretty_name():
    return _("Install Systemd-boot.")

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


def create_conf(uuid, conf_path):
    distribution = libcalamares.job.configuration["distribution"]
    kernel = libcalamares.job.configuration["kernel"]
    img = libcalamares.job.configuration["img"]
    partitions = libcalamares.globalstorage.value("partitions")

    kernel_params = ["quiet systemd.show_status=0"]
    swap = ""
    swap_luks = ""
    cryptdevice_params = []
    btrfs_params = ""

    for partition in partitions:
        if partition["fs"] == "linuxswap" and not "luksMapperName" in partition:
            swap = partition["uuid"]

        if partition["fs"] == "linuxswap" and "luksMapperName" in partition:
            swap_luks = partition["luksMapperName"]

        if partition["mountPoint"] == "/" and "luksMapperName" in partition:
            cryptdevice_params = [
                "cryptdevice=UUID={!s}:{!s}".format(partition["luksUuid"],
                                                    partition["luksMapperName"]),
                "root=/dev/mapper/{!s}".format(partition["luksMapperName"]),
                "resume=/dev/mapper/{!s}".format(partition["luksMapperName"])
            ]

        # systemd-boot with a BTRFS root filesystem needs to be told
        # about the root subvolume.
        if partition["mountPoint"] == "/" and partition["fs"] == "btrfs":
            btrfs_params = "rootflags=subvol=@"

    if cryptdevice_params:
        kernel_params.extend(cryptdevice_params)
    else:
        kernel_params.append("root=UUID={!s}".format(uuid))

    if swap:
        kernel_params.append("resume=UUID={!s}".format(swap))
    if swap_luks:
        kernel_params.append("resume=/dev/mapper/{!s}".format(swap_luks))
    if btrfs_params:
        print('BTRFS')
        kernel_params.append(btrfs_params)

    lines = [
        '## Please edit the paths and kernel parameters according to your system.\n',
        '\n',
        'title   {!s} GNU/Linux, with Linux kernel (Type h or ? for a Help menu)\n'.format(distribution),
        'linux   {!s}\n'.format(kernel),
        'initrd  {!s}\n'.format(img),
        'options {!s} rw\n'.format(" ".join(kernel_params)),
    ]

    with open(conf_path, 'w') as f:
        for l in lines:
            f.write(l)
    f.close()


def create_fallback(uuid, fallback_path):
    distribution = libcalamares.job.configuration["distribution"]
    kernel = libcalamares.job.configuration["kernel"]
    fb_img = libcalamares.job.configuration["fallback"]
    partitions = libcalamares.globalstorage.value("partitions")

    kernel_params = ["quiet systemd.show_status=0"]
    swap = ""
    cryptdevice_params = []

    for partition in partitions:
        if partition["fs"] == "linuxswap":
            swap = partition["uuid"]

        if partition["mountPoint"] == "/" and "luksMapperName" in partition:
            cryptdevice_params = [
                "cryptdevice=UUID={!s}:{!s}".format(partition["luksUuid"],
                                                    partition["luksMapperName"]),
                "root=/dev/mapper/{!s}".format(partition["luksMapperName"])
            ]

    if cryptdevice_params:
        kernel_params.extend(cryptdevice_params)
    else:
        kernel_params.append("root=UUID={!s}".format(uuid))

    if swap:
        kernel_params.append("resume=UUID={!s}".format(swap))

    lines = [
        '## Please edit the paths and kernel parameters according to your system.\n',
        '\n',
        'title   {!s} GNU/Linux, with Linux fallback kernel\n'.format(distribution),
        'linux   {!s}\n'.format(kernel),
        'initrd  {!s}\n'.format(fb_img),
        'options {!s} rw\n'.format(" ".join(kernel_params)),
    ]

    with open(fallback_path, 'w') as f:
        for l in lines:
            f.write(l)
    f.close()


def create_loader(loader_path):
    distribution = libcalamares.job.configuration["distribution"]
    timeout = libcalamares.job.configuration["timeout"]
    lines = [
        'timeout {!s}\n'.format(timeout),
        'default {!s}\n'.format(distribution),
    ]

    with open(loader_path, 'w') as f:
        for l in lines:
            f.write(l)
    f.close()


def install_systemd_boot(boot_loader):
    install_path = libcalamares.globalstorage.value("rootMountPoint")
    uuid = get_uuid()
    distribution = libcalamares.job.configuration["distribution"]
    conf_path = os.path.join(
        install_path, "boot", "loader", "entries",
        "{!s}.conf".format(distribution))
    fallback_path = os.path.join(
        install_path, "boot", "loader", "entries", "{!s}-fallback.conf".format(distribution))
    loader_path = os.path.join(
        install_path, "boot", "loader", "loader.conf")
    partitions = libcalamares.globalstorage.value("partitions")
    device = ""

    for partition in partitions:
        if partition["mountPoint"] == "/boot":
            libcalamares.utils.debug(partition["device"])
            boot_device = partition["device"]
            boot_p = boot_device[-1:]
            device = boot_device[:-1]
            if boot_device.startswith('/dev/nvme'):
                device = boot_device[:-2]

            if not boot_p or not device:
                return ("EFI directory /boot not found!",
                        "Boot partition: \"{!s}\"",
                        "Boot device: \"{!s}\"".format(boot_p, device))
            else:
                print("EFI directory: /boot")
                print("Boot partition: \"{!s}\"".format(boot_p))
                print("Boot device: \"{!s}\"".format(device))

    if not device:
        print("WARNING: no EFI system partition or EFI system partition mount point not set.")
        print("         >>> no EFI bootloader will be installed <<<")
        return None
    print("Set 'EF00' flag")
    subprocess.call(
        ["sgdisk", "--typecode={!s}:EF00".format(boot_p), "{!s}".format(device)])
    subprocess.call(
        ["bootctl", "--path={!s}/boot".format(install_path), "install"])
    create_conf(uuid, conf_path)
    create_fallback(uuid, fallback_path)
    create_loader(loader_path)


def run():
    boot_loader = libcalamares.globalstorage.value("bootLoader")
    # Packagechooser@bootchoice outcome
    bootchoice = libcalamares.globalstorage.value("packagechooser_bootchoice")

    if bootchoice != 'systemd-boot':
        return None

    install_systemd_boot(boot_loader)
    return None
