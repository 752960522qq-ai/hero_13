using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

public static class SmokeBuild
{
    public static void Build()
    {
        Debug.Log($"UNITY_SMOKE_OK editor={Application.unityVersion} platform={Application.platform}");
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        var cameraObject = new GameObject("Main Camera");
        cameraObject.tag = "MainCamera";
        cameraObject.AddComponent<Camera>();
        var lightObject = new GameObject("Directional Light");
        lightObject.AddComponent<Light>().type = LightType.Directional;
        var scenePath = "Assets/SmokeTest.unity";
        EditorSceneManager.SaveScene(scene, scenePath);
        var output = Path.GetFullPath("Build/hero_13-smoke.x86_64");
        Directory.CreateDirectory(Path.GetDirectoryName(output));
        var options = new BuildPlayerOptions
        {
            scenes = new[] { scenePath },
            locationPathName = output,
            target = BuildTarget.StandaloneLinux64,
            options = BuildOptions.None
        };
        var report = BuildPipeline.BuildPlayer(options);
        Debug.Log($"UNITY_BUILD_RESULT result={report.summary.result} errors={report.summary.totalErrors} warnings={report.summary.totalWarnings} output={output}");
        if (report.summary.result != UnityEditor.Build.Reporting.BuildResult.Succeeded)
            throw new System.Exception("Unity smoke build failed: " + report.summary.result);
    }
}
