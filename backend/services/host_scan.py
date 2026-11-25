"""Fixed, read-only Windows posture checks. Never execute user-supplied commands."""
import json
import platform
import subprocess
from datetime import datetime, timezone

CHECKS = (
    ("defender", "Microsoft Defender", "Get-MpComputerStatus -ErrorAction Stop | Select-Object AntivirusEnabled,RealTimeProtectionEnabled,AntivirusSignatureAge", "Open Windows Security → Virus & threat protection. Enable protection and check for updates."),
    ("firewall", "Windows Firewall", "@(Get-NetFirewallProfile -ErrorAction Stop | Select-Object Name,Enabled) | ConvertTo-Json -Compress", "Open Windows Security → Firewall & network protection. Enable the firewall for each network profile."),
    ("encryption", "System drive encryption", "Get-BitLockerVolume -MountPoint $env:SystemDrive -ErrorAction Stop | Select-Object ProtectionStatus", "Review Device encryption or Manage BitLocker. Back up your recovery key before enabling encryption."),
    ("uac", "User Account Control", "Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System' -ErrorAction Stop | Select-Object EnableLUA", "Open User Account Control settings and review the notification level. Restart if Windows requests it."),
    ("updates", "Recent installed update", "Get-HotFix -ErrorAction Stop | Where-Object InstalledOn | Sort-Object InstalledOn -Descending | Select-Object -First 1 @{Name='AgeDays';Expression={[int]((Get-Date)-$_.InstalledOn).TotalDays}}", "Open Settings → Windows Update and check for updates. Hotfix history does not prove patch completeness."),
)


def evaluate(key, data):
    if key == "defender":
        healthy = data.get("AntivirusEnabled") is True and data.get("RealTimeProtectionEnabled") is True
        age = data.get("AntivirusSignatureAge")
        return ("pass" if healthy and isinstance(age, (int, float)) and age <= 3 else "warning",
                f"Antivirus enabled: {data.get('AntivirusEnabled')}; real-time protection: {data.get('RealTimeProtectionEnabled')}; signature age: {age} days. Other antivirus products are not assessed.")
    if key == "firewall":
        rows = data if isinstance(data, list) else [data]
        healthy = bool(rows) and all(row.get("Enabled") in (True, 1) for row in rows)
        return ("pass" if healthy else "warning", "; ".join(f"{row.get('Name')}: {'enabled' if row.get('Enabled') in (True, 1) else 'disabled'}" for row in rows))
    if key == "encryption":
        enabled = data.get("ProtectionStatus") in (1, "On")
        return ("pass" if enabled else "warning", f"System drive protection status: {data.get('ProtectionStatus')} (1 / On means protected).")
    if key == "uac":
        return ("pass" if data.get("EnableLUA") == 1 else "warning", f"EnableLUA: {data.get('EnableLUA')} (1 means enabled). Notification level is not assessed.")
    age = data.get("AgeDays")
    return ("pass" if isinstance(age, (int, float)) and age <= 35 else "warning", f"Most recent hotfix age: {age} days. Verify current patch status in Windows Update.")


def scan():
    if platform.system() != "Windows":
        raise ValueError("Run the Python backend directly on your Windows laptop. A Linux or Docker backend cannot scan the Windows host.")
    findings = []
    for key, title, command, guidance in CHECKS:
        # Firewall already serializes an array; all other commands return one object.
        script = "$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8; " + command
        if key != "firewall":
            script += " | ConvertTo-Json -Compress"
        try:
            result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=True)
            data = json.loads(result.stdout.strip())
            if not data or not isinstance(data, (dict, list)):
                raise ValueError("No result")
            status, evidence = evaluate(key, data)
        except (subprocess.SubprocessError, OSError, ValueError, TypeError, AttributeError):
            status, evidence = "unknown", "Check unavailable. Windows edition, permissions, policy, or a missing component may prevent this check."
        findings.append(dict(id=key, title=title, status=status, evidence=evidence, guidance=guidance))
    return dict(scanned_at=datetime.now(timezone.utc).isoformat(), platform="Windows", mode="read-only",
                findings=findings, summary={s: sum(f["status"] == s for f in findings) for s in ("pass", "warning", "unknown")},
                limitations="A posture scan, not malware detection or a complete vulnerability assessment. No personal files were read, no settings changed, and no scan data sent to an AI provider.")
