# Windows EXE release

Deze map is klaar om als Windows portable EXE-release te worden gebouwd.

## Lokaal bouwen

1. Installeer 64-bit Python 3.11.
2. Start `start_converter.bat` en laat de installatie afronden.
3. Sluit de applicatie.
4. Start `build_windows_exe.bat`.

Output:

```text
dist\NC1_STEP_Converter\NC1_STEP_Converter.exe
dist\NC1_STEP_Converter_Windows_x64.zip
```

## Bouwen via GitHub Actions

De workflow staat in:

```text
.github/workflows/build-windows-exe.yml
```

Ga in GitHub naar **Actions → Build Windows EXE → Run workflow**. Het artifact heet:

```text
NC1_STEP_Converter_Windows_x64
```

## Waarom geen losse .exe in deze ZIP?

CadQuery/Open CASCADE/IfcOpenShell hebben veel DLL's en data nodig. De betrouwbare distributievorm is daarom een portable map- of ziprelease. Deze Linuxomgeving kan geen native Windows-runner vervangen; de meegeleverde workflow/script bouwen de echte Windows x64 release op Windows.
