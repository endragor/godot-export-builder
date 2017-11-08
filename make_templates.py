import os, sys, imp, shutil
from subprocess import call
from contextlib import contextmanager

@contextmanager
def dir(directory):
  owd = os.getcwd()
  try:
    os.chdir(directory)
    yield directory
  finally:
    os.chdir(owd)

jobs_arg = "-j4"

def call_or_die(cmd):
  print "EXEC: " + " ".join(cmd)
  ret = call(cmd)
  if ret != 0:
    print "Last command returned " + str(ret) + " - quitting."
    sys.exit(ret)

def build_android(target_dir, additional_params):
  call_or_die(["scons", jobs_arg, "tools=no", "p=android", "android_stl=true", "target=release", "ndk_unified_headers=no"] + additional_params)
  with dir("platform/android/java"):
    call_or_die(["./gradlew", "build"])
  shutil.copyfile("bin/android_release.apk", target_dir + "/android_release.apk")

  call_or_die(["scons", jobs_arg, "tools=no", "p=android", "android_stl=true", "target=debug", "ndk_unified_headers=no"] + additional_params)
  with dir("platform/android/java"):
    call_or_die(["./gradlew", "build"])
  shutil.copyfile("bin/android_debug.apk", target_dir + "/android_debug.apk")

def build_iphone(target_dir, additional_params):
  call_or_die(["scons", jobs_arg, "tools=no", "bits=32", "p=iphone", "target=release", "arch=arm"] + additional_params)
  call_or_die(["scons", jobs_arg, "tools=no", "bits=64", "p=iphone", "target=release", "arch=arm64"] + additional_params)
  shutil.copyfile("bin/godot.iphone.opt.arm", "misc/dist/ios_xcode/godot.iphone.release.arm")
  shutil.copyfile("bin/godot.iphone.opt.arm64", "misc/dist/ios_xcode/godot.iphone.release.arm64")
  call_or_die(["lipo", "-create", "bin/godot.iphone.opt.arm", "bin/godot.iphone.opt.arm64", "-output", "misc/dist/ios_xcode/godot.iphone.release.fat"])

  call_or_die(["scons", jobs_arg, "tools=no", "bits=32", "p=iphone", "target=debug", "arch=arm"] + additional_params)
  call_or_die(["scons", jobs_arg, "tools=no", "bits=64", "p=iphone", "target=debug", "arch=arm64"] + additional_params)
  shutil.copyfile("bin/godot.iphone.debug.arm", "misc/dist/ios_xcode/godot.iphone.debug.arm")
  shutil.copyfile("bin/godot.iphone.debug.arm64", "misc/dist/ios_xcode/godot.iphone.debug.arm64")
  call_or_die(["lipo", "-create", "bin/godot.iphone.debug.arm", "bin/godot.iphone.debug.arm64", "-output", "misc/dist/ios_xcode/godot.iphone.debug.fat"])

  with dir("misc/dist/ios_xcode"):
    call_or_die(["zip", "-r9", target_dir + "/iphone.zip", ".", "-i", "*"])

def build_osx(target_dir, additional_params):
  binary_dir = "misc/dist/osx_template.app/Contents/MacOS/"
  if not os.path.exists(binary_dir):
    os.makedirs(binary_dir)

  call_or_die(["scons", jobs_arg, "tools=no", "p=osx", "bits=64", "target=release_debug"] + additional_params)
  shutil.copyfile("bin/godot.osx.opt.debug.64", binary_dir + "godot_osx_debug.64")

  call_or_die(["scons", jobs_arg, "tools=no", "p=osx", "bits=64", "target=release"] + additional_params)
  shutil.copyfile("bin/godot.osx.opt.64", binary_dir + "godot_osx_release.64")

  with dir("misc/dist"):
    call_or_die(["zip", "-r9", target_dir + "/osx.zip", "osx_template.app"])

def aggregate_by_platform(params, platforms):
  ret = {}
  used_params = set()
  for platform in platforms:
    platform_params = []
    for i, param in enumerate(params):
      if param.startswith(platform + ":"):
        platform_params.append(param[len(platform + ":"):])
        used_params.add(i)
    ret[platform] = platform_params

  for i, param in enumerate(params):
    if i not in used_params:
      print "Bad parameter: " + param
      sys.exit(1)

  return ret

if __name__ == "__main__":
  if len(sys.argv) < 4:
    print "Usage: python make_templates.py <godot_src_dir> <templates_dir> <comma_separated_platforms>"
    sys.exit(1)

  godot_src = sys.argv[1]
  target_root_dir = sys.argv[2]
  platforms = sys.argv[3].split(",")

  version = imp.load_source("godot.version", godot_src + "/version.py")
  version_str = str(version.major) + "." + str(version.minor) + "-" + version.status

  target_dir = target_root_dir + "/" + version_str

  if not os.path.exists(target_dir):
    os.makedirs(target_dir)
  with open(target_dir + "/version.txt", "w") as f:
    f.write(version_str)

  exit_code = 0
  builders = {
    "android": build_android,
    "iphone": build_iphone,
    "osx": build_osx
  }
  aggregated_params = aggregate_by_platform(sys.argv[4:], builders)
  with dir(godot_src):
    for platform in platforms:
      if platform in builders:
        builders[platform](target_dir, aggregated_params[platform])
      else:
        print("Unknown platform: " + platform)
        exit_code = 1

  sys.exit(exit_code)
