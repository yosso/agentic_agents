param([Parameter(Mandatory=$true)][string]$RequestPath,
      [Parameter(Mandatory=$true)][string]$ResultPath)
$ErrorActionPreference = 'Stop'
$request = Get-Content -LiteralPath $RequestPath -Raw | ConvertFrom-Json
$output = @{ groups = @(); reactions = @(); warnings = @(); error = $null }
$robot = $null
$ownsRobot = $false
try {
    Add-Type -Path $request.api
    if (Get-Process robot -ErrorAction SilentlyContinue) {
        Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class RunningRobot {
    [DllImport("oleaut32.dll", PreserveSig=false)]
    private static extern void GetActiveObject(ref Guid clsid, IntPtr reserved,
        [MarshalAs(UnmanagedType.IUnknown)] out object result);
    public static object Get() {
        Guid id = new Guid("F7870790-CDE5-11D1-8FF1-00A02447BAAE");
        object result; GetActiveObject(ref id, IntPtr.Zero, out result); return result;
    }
}
'@
        try { $robot = [RobotOM.IRobotApplication][RunningRobot]::Get() }
        catch { throw 'Robot is running but its API is unavailable. Close Robot and try again, or open the mapped model in a ready Robot session.' }
        $output.warnings += 'Reading the open Robot session only. Other model files will be skipped; no projects will be switched or closed.'
    } else {
        $robot = New-Object RobotOM.RobotApplicationClass
        if ($robot.Project.IsActive) { throw 'Robot returned an active project unexpectedly; no changes made.' }
        $ownsRobot = $true
        $robot.Visible = 0
        $robot.Interactive = 0
    }
    foreach ($fileGroup in ($request.mappings | Group-Object model)) {
        try {
            if (-not (Test-Path -LiteralPath $fileGroup.Name -PathType Leaf)) {
                throw "Model file not found: $($fileGroup.Name)"
            }
            if ($ownsRobot) {
                $robot.Project.Open($fileGroup.Name)
            } elseif (-not $robot.Project.IsActive -or
                [IO.Path]::GetFullPath($robot.Project.FileName) -ne [IO.Path]::GetFullPath($fileGroup.Name)) {
                throw 'This model is not the open Robot project. Close Robot to read multiple model files in a separate session.'
            }
            $structure = $robot.Project.Structure
            $resultsReady = ([int]$structure.Results.Status -eq 1 -and $structure.Results.Available)
            $cases = @()
            $allCases = $structure.Cases.GetAll()
            $foundCases = @()
            for ($ci = 1; $ci -le $allCases.Count; $ci++) {
                $case = $allCases.Get($ci)
                $caseId = [int]$case.Number
                $foundCases += $caseId
                if ($request.cases.Count -gt 0 -and $caseId -notin $request.cases) { continue }
                # Simple load cases are never extracted, even if explicitly requested.
                if ([int]$case.Type -eq 0) {
                    if ($request.cases.Count -gt 0) {
                        $output.warnings += "Skipped $caseId ($($case.Name)): a load case, not a load combination."
                    }
                    continue
                }
                # Ordinary linear combinations use Value; envelope/incremental
                # combinations still require component-specific extraction.
                if ([int]$case.Type -eq 1 -and [int]$case.AnalizeType -eq 0) {
                    $cases += @{ id=$caseId; name=[string]$case.Name }
                } else {
                    $output.warnings += "Skipped $caseId ($($case.Name)) in $($fileGroup.Name): not a supported ordinary linear combination (type $($case.Type), analysis $($case.AnalizeType))."
                }
            }
            foreach ($missing in $request.cases) {
                if ($missing -notin $foundCases) { $output.warnings += "Requested combination $missing not found in $($fileGroup.Name)." }
            }
            foreach ($mapping in $fileGroup.Group) {
                $summary = @{ mark=$mapping.mark; model=$mapping.model; group=$mapping.group;
                    expected=$mapping.expected; node_count=$null; support_count=$null; nodes=@(); status=''; result_rows=0 }
                try {
                    $index = $structure.Groups.Find([RobotOM.IRobotObjectType]::I_OT_NODE, $mapping.group)
                    if ($index -le 0) { throw "Node group not found: $($mapping.group)" }
                    $group = $structure.Groups.Get([RobotOM.IRobotObjectType]::I_OT_NODE, $index)
                    $selection = $group.CreateSelection()
                    $nodes = @()
                    for ($ni = 1; $ni -le $selection.Count; $ni++) { $nodes += [int]$selection.Get($ni) }
                    $nodes = @($nodes | Sort-Object -Unique)
                    $summary.nodes = $nodes
                    $summary.node_count = $nodes.Count
                    $summary.support_count = 0
                    if ($nodes.Count -eq 0) { throw 'Group has no nodes.' }
                    $issues = @()
                    if ($nodes.Count -ne $mapping.expected) { $issues += 'Quantity mismatch' }
                    if (-not $resultsReady) { $issues += 'Results missing or out of date; no reactions read' }
                    if ($cases.Count -eq 0) { $issues += 'No supported load combinations selected' }
                    foreach ($nodeId in $nodes) {
                        $node = $structure.Nodes.Get($nodeId)
                        if (-not ($node.HasLabel([RobotOM.IRobotLabelType]::I_LT_NODE_SUPPORT) -or $node.HasCalcSupport)) {
                            $issues += "Node $nodeId is not a support"
                            continue
                        }
                        $summary.support_count++
                        if (-not $resultsReady) { continue }
                        foreach ($case in $cases) {
                            try {
                                $reaction = $structure.Results.Nodes.Reactions.Value($nodeId, $case.id)
                                $record = @{mark=$mapping.mark; model=$mapping.model; group=$mapping.group;
                                    node=$nodeId; case=$case.id; case_name=$case.name}
                                foreach ($component in @('FX','FY','FZ','MX','MY','MZ')) {
                                    $value = [double]$reaction.$component
                                    if ([double]::IsNaN($value) -or [double]::IsInfinity($value)) { throw 'Non-finite reaction value' }
                                    $record[$component] = $value
                                }
                                $output.reactions += $record
                                $summary.result_rows++
                            } catch {
                                $issues += "Node $nodeId / combination $($case.id): $($_.Exception.Message)"
                            }
                        }
                    }
                    $summary.status = if ($issues.Count) { ($issues | Select-Object -Unique) -join '; ' } else { 'OK' }
                } catch { $summary.status = $_.Exception.Message }
                $output.groups += $summary
            }
        } catch {
            foreach ($mapping in $fileGroup.Group) {
                $output.groups += @{mark=$mapping.mark; model=$mapping.model; group=$mapping.group;
                    expected=$mapping.expected; node_count=$null; support_count=$null; nodes=@();
                    result_rows=0; status=$_.Exception.Message}
            }
        } finally {
            if ($ownsRobot -and $robot.Project.IsActive) { $robot.Project.Close() }
        }
    }
} catch { $output.error = $_.Exception.Message }
finally {
    if ($ownsRobot) {
        try { $robot.Quit([RobotOM.IRobotQuitOption]::I_QO_DISCARD_CHANGES) } catch { $output.warnings += "Robot cleanup: $($_.Exception.Message)" }
    }
    $output | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $ResultPath -Encoding UTF8
}
