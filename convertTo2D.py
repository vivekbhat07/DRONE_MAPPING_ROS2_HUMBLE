import open3d as o3d
import numpy as np

pcd = o3d.io.read_point_cloud("map.pcd_cloud.ply")
points = np.asarray(pcd.points)

# filter height (Z axis)
z_min = -1.0
z_max = 0.2

mask = (points[:,2] > z_min) & (points[:,2] < z_max)
filtered = pcd.select_by_index(np.where(mask)[0])

# project to 2D (remove height)
points_2d = np.asarray(filtered.points)
points_2d[:,2] = 0

filtered.points = o3d.utility.Vector3dVector(points_2d)

o3d.io.write_point_cloud("map_2d.pcd", filtered)
print("2D map saved successfully ✅")
