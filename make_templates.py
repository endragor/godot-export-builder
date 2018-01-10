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

jobs_arg = "-j8"

def call_or_die(cmd):
  print "EXEC: " + " ".join(cmd)
  ret = call(cmd)
  if ret != 0:
    print "Last command returned " + str(ret) + " - quitting."
    sys.exit(ret)

def copyfile(source, dest, buf_size = 1024*1024):
  with open(source, 'rb') as src, open(dest, 'wb') as dst:
    while True:
      copy_buffer = src.read(buf_size)
      if not copy_buffer:
        break
      dst.write(copy_buffer)

def build_android(target_dir, additional_params):
  call_or_die(["scons", jobs_arg, "tools=no", "p=android", "android_stl=true", "target=release", "ndk_unified_headers=no"] + additional_params)
  with dir("platform/android/java"):
    call_or_die(["./gradlew", "build"])
  copyfile("bin/android_release.apk", target_dir + "/android_release.apk")
  release_symbols = "bin/libgodot_symbols.android.release.so"
  if os.path.exists(release_symbols):
    copyfile(release_symbols, target_dir + "/libgodot_symbols.android.release.so")

  call_or_die(["scons", jobs_arg, "tools=no", "p=android", "android_stl=true", "target=release_debug", "ndk_unified_headers=no"] + additional_params)
  with dir("platform/android/java"):
    call_or_die(["./gradlew", "build"])
  copyfile("bin/android_debug.apk", target_dir + "/android_debug.apk")
  debug_symbols = "bin/libgodot_symbols.android.debug.so"
  if os.path.exists(debug_symbols):
    copyfile(debug_symbols, target_dir + "/libgodot_symbols.android.debug.so")

def build_iphone(target_dir, additional_params):
  archs = ["arm", "arm64", "x86", "x86_64"]
  for arch in archs:
    call_or_die(["scons", jobs_arg, "tools=no", "p=iphone", "target=release", "arch=" + arch] + additional_params)
    call_or_die(["scons", jobs_arg, "tools=no", "p=iphone", "target=release_debug", "arch=" + arch] + additional_params)

  call_or_die(["lipo", "-create"] + map(lambda arch: "bin/libgodot.iphone.opt." + arch + ".a", archs) + ["-output", "misc/dist/ios_xcode/libgodot.iphone.release.fat.a"])
  call_or_die(["lipo", "-create"] + map(lambda arch: "bin/libgodot.iphone.opt.debug." + arch + ".a", archs) + ["-output", "misc/dist/ios_xcode/libgodot.iphone.debug.fat.a"])

  with dir("misc/dist/ios_xcode"):
    call_or_die(["zip", "-r9", target_dir + "/iphone.zip", ".", "-i", "*"])

def build_osx(target_dir, additional_params):
  binary_dir = "misc/dist/osx_template.app/Contents/MacOS/"
  if not os.path.exists(binary_dir):
    os.makedirs(binary_dir)

  call_or_die(["scons", jobs_arg, "tools=no", "p=osx", "bits=64", "target=release_debug"] + additional_params)
  copyfile("bin/godot.osx.opt.debug.64", binary_dir + "godot_osx_debug.64")

  call_or_die(["scons", jobs_arg, "tools=no", "p=osx", "bits=64", "target=release"] + additional_params)
  copyfile("bin/godot.osx.opt.64", binary_dir + "godot_osx_release.64")

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

  target_dir = os.path.expanduser(target_root_dir) + "/" + version_str

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
