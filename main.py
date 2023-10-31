import os
import subprocess
import sys
#import utils

# General options
ARCH = os.getenv("ARCH", "x86_64")
PLATFORM = os.getenv("PLATFORM", "")
SMP = int(os.getenv("SMP", "1"))
MODE = os.getenv("MODE", "release")
LOG = os.getenv("LOG", "warn")
V = os.getenv("V", "")

# App options
A = os.getenv("A", "apps/helloworld")
APP = A
FEATURES = os.getenv("FEATURES", "")
APP_FEATURES = os.getenv("APP_FEATURES", "")

# QEMU options
BLK = os.getenv("BLK", "n")
NET = os.getenv("NET", "n")
GRAPHIC = os.getenv("GRAPHIC", "n")
BUS = os.getenv("BUS", "mmio")

DISK_IMG = os.getenv("DISK_IMG", "disk.img")
QEMU_LOG = os.getenv("QEMU_LOG", "n")
NET_DUMP = os.getenv("NET_DUMP", "n")
NET_DEV = os.getenv("NET_DEV", "user")

# Network options
IP = os.getenv("IP", "10.0.2.15")
GW = os.getenv("GW", "10.0.2.2")

# App type
if not os.path.exists(APP):
    raise ValueError(f"Application path \"{APP}\" is not valid")

if os.path.exists(os.path.join(APP, "Cargo.toml")):
    APP_TYPE = "rust"
else:
    APP_TYPE = "c"

# Architecture, platform and target
if any(arg in ('unittest', 'unittest_no_fail_fast') for arg in sys.argv):
    PLATFORM_NAME = ""
elif PLATFORM:
    # `PLATFORM` is specified, override the `ARCH` variables
    builtin_platforms = [p.split(".")[0] for p in os.listdir("platforms")]
    if PLATFORM in builtin_platforms:
        # builtin platform
        PLATFORM_NAME = PLATFORM
        _arch = PLATFORM.split("-")[0]
    elif os.path.exists(PLATFORM):
        # custom platform, read the "platform" field from the toml file
        with open(PLATFORM, "r") as f:
            for line in f:
                if line.startswith("platform ="):
                    PLATFORM_NAME = line.split('"')[1]
                elif line.startswith("arch ="):
                    _arch = line.split('"')[1]
                    break
    else:
        raise ValueError(f"\"PLATFORM\" must be one of {builtin_platforms} or a valid path to a toml file")

    if os.getenv("ARCH") and ARCH != _arch:
        raise ValueError(f"\"ARCH={ARCH}\" is not compatible with \"PLATFORM={PLATFORM}\"")
    ARCH = _arch

if ARCH == "x86_64":
    # Don't enable kvm for WSL/WSL2.
    ACCEL = "n" if "-microsoft" in os.uname().lower() else "y"
    PLATFORM_NAME = "x86_64-qemu-q35"
    TARGET = "x86_64-unknown-none"
    BUS = "pci"
elif ARCH == "riscv64":
    ACCEL = "n"
    PLATFORM_NAME = "riscv64-qemu-virt"
    TARGET = "riscv64gc-unknown-none-elf"
elif ARCH == "aarch64":
    ACCEL = "n"
    PLATFORM_NAME = "aarch64-qemu-virt"
    TARGET = "aarch64-unknown-none-softfloat"
else:
    raise ValueError("\"ARCH\" must be one of \"x86_64\", \"riscv64\", or \"aarch64\"")

os.environ["AX_ARCH"] = ARCH
os.environ["AX_PLATFORM"] = PLATFORM_NAME
os.environ["AX_SMP"] = str(SMP)
os.environ["AX_MODE"] = MODE
os.environ["AX_LOG"] = LOG
os.environ["AX_TARGET"] = TARGET
os.environ["AX_IP"] = IP
os.environ["AX_GW"] = GW

# Binutils
CROSS_COMPILE = f"{ARCH}-linux-musl-"
CC = f"{CROSS_COMPILE}gcc"
AR = f"{CROSS_COMPILE}ar"
RANLIB = f"{CROSS_COMPILE}ranlib"
LD = "rust-lld -flavor gnu"

OBJDUMP = f"rust-objdump -d --print-imm-hex --x86-asm-syntax=intel"
OBJCOPY = f"rust-objcopy --binary-architecture={ARCH}"
GDB = "gdb-multiarch"

# Paths
OUT_DIR = APP

APP_NAME = os.path.basename(APP)
LD_SCRIPT = os.path.join(os.getcwd(), f"modules/axhal/linker_{PLATFORM_NAME}.lds")
OUT_ELF = os.path.join(OUT_DIR, f"{APP_NAME}_{PLATFORM_NAME}.elf")
OUT_BIN = os.path.join(OUT_DIR, f"{APP_NAME}_{PLATFORM_NAME}.bin")


def run_command(cmd):
    process = subprocess.Popen(cmd, shell=True)
    process.communicate()


def build():
    run_command(f"make -f scripts/make/build.mk OUT_DIR={OUT_DIR} OUT_BIN={OUT_BIN} APP_TYPE={APP_TYPE}")


def disasm():
    run_command(f"{OBJDUMP} {OUT_ELF} | less")


# def run():
#     build()
#     run_qemu()


# def justrun():
#     run_qemu()




def clippy():
    if ARCH:
        run_command(f"make -f scripts/make/utils.mk OUT_DIR={OUT_DIR} APP={APP} ARCH={ARCH} cargo_clippy")
    else:
        run_command(f"make -f scripts/make/utils.mk OUT_DIR={OUT_DIR} APP={APP} cargo_clippy")


def doc():
    run_command(f"make -f scripts/make/utils.mk doc")


def doc_check_missing():
    run_command(f"make -f scripts/make/utils.mk doc_check_missing")


def fmt():
    run_command("cargo fmt --all")


def fmt_c():
    run_command(f"clang-format --style=file -i $(shell find ulib/axlibc -iname '*.c' -o -iname '*.h')")


def test():
    run_command(f"make -f scripts/make/utils.mk OUT_DIR={OUT_DIR} APP={APP} test_no_fail_fast")


def unittest():
    run_command(f"make -f scripts/make/utils.mk OUT_DIR={OUT_DIR} unit_test")


def unittest_no_fail_fast():
    run_command(f"make -f scripts/make/utils.mk OUT_DIR={OUT_DIR} unit_test_no_fail_fast")


def disk_img():
    if os.path.exists(DISK_IMG):
        print(f"warning: disk image \"{DISK_IMG}\" already exists!")
    else:
        run_command(f"make -f scripts/make/utils.mk disk_image FAT_FORMAT=fat32 DISK_IMG={DISK_IMG}")


def clean():
    run_command(f"make -f scripts/make/utils.mk OUT_DIR={OUT_DIR} clean clean_c")
    os.remove(OUT_BIN)
    os.remove(OUT_ELF)


def clean_c():
    run_command(f"make -f scripts/make/utils.mk clean_c")


if __name__ == "__main__":
    target = os.getenv("TARGET", "")
    if target == "build":
        build()
    elif target == "disasm":
        disasm()
    # elif target == "run":
    #     run()
    # elif target in ["justrun", "just_run"]:
    #     justrun()
    # elif target == "debug":
    #     debug()
    elif target == "clippy":
        clippy()
    elif target == "doc":
        doc()
    elif target == "doc_check_missing":
        doc_check_missing()
    elif target == "fmt":
        fmt()
    elif target == "fmt_c":
        fmt_c()
    elif target == "test":
        test()
    elif target == "unittest":
        unittest()
    elif target == "unittest_no_fail_fast":
        unittest_no_fail_fast()
    elif target == "disk_img":
        disk_img()
    elif target == "clean":
        clean()
    elif target == "clean_c":
        clean_c()
    else:
        print("Please provide a valid target.")
