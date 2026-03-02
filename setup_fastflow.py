from distutils.core import setup, Extension

fastflow_ext = Extension(
    "fastflow",
    sources=["fastflowmodule.c"],
    extra_compile_args=["-O3"],
)

setup(
    name="fastflow",
    version="0.1.0",
    ext_modules=[fastflow_ext],
)
