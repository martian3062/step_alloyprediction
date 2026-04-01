import trimesh
import os
import sys

def test_load(file_path):
    print(f"Testing load for: {file_path}")
    try:
        mesh = trimesh.load(file_path)
        print(f"Loaded: {type(mesh)}")
        if isinstance(mesh, trimesh.Scene):
            print(f"Geometries: {list(mesh.geometry.keys())}")
            for name, g in mesh.geometry.items():
                print(f"  {name}: volume={g.volume}, area={g.area}")
        else:
            print(f"Volume: {mesh.volume}, Area: {mesh.area}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_load(sys.argv[1])
    else:
        print("Please provide a file path.")
