<#
.SYNOPSIS
Deletes all ZIP files matching mechanical machines listed in an XML manifest.

.PARAMETER XmlFile
Path to the XML file containing <machine name="…" /> entries.
Default: "mechanical_only.xml"

.PARAMETER ZipFolder
Folder where your ZIPs live (defaults to the current directory).
#>
param(
  [string]$XmlFile   = "mechanical_only.xml",
  [string]$ZipFolder = "."
)

# 1. Load the XML document
try {
    [xml]$doc = Get-Content $XmlFile -ErrorAction Stop
} catch {
    Write-Error "Could not load XML file '$XmlFile': $_"
    exit 1
}

# 2. Select every <machine> node
$nodes = $doc.SelectNodes("//machine")

if (-not $nodes) {
    Write-Warning "No <machine> nodes found in '$XmlFile'."
    exit 0
}

Write-Host "Deleting $($nodes.Count) mechanical machine ZIP(s) from '$ZipFolder'..."

foreach ($node in $nodes) {
    # 3. Read the 'name' attribute
    $name = $node.Attributes["name"].Value

    # 4. Build the full path to the ZIP
    $zipPath = Join-Path -Path $ZipFolder -ChildPath ("$name.zip")

    if (Test-Path $zipPath) {
        # 5. Delete without confirmation prompts
        Write-Host "Deleting: $zipPath"
        Remove-Item $zipPath -Force -Confirm:$false
    } else {
        Write-Warning "Not found, skipping: $zipPath"
    }
}

Write-Host "Done."  
