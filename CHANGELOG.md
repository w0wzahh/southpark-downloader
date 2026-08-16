# Changelog

All notable changes to South Park Downloader are documented in this file.

The project follows [Semantic Versioning](https://semver.org/).

---

## [3.7.3] - 2026-08-16

### Fixed

- Fixed Windows release packaging.
- Fixed the Windows installer packaging configuration.
- Updated the Inno Setup configuration used to generate the Windows installer.
- Updated the installer to package the generated PyInstaller executable directly.
- Fixed installer output generation for the `3.7.3` release.
- Removed the previous 64-bit installation mode restriction from the installer configuration to improve Windows installation compatibility.
- Improved the Windows release workflow and packaging configuration.

### Release Artifacts

The Windows installer for this release is:

```text
SouthParkDownloader-Setup-3.7.3.exe
```

The installer is generated using Inno Setup 6 from the PyInstaller-built application.

---

## [3.7.2] - 2026-08-16

### Fixed

- Fixed Inno Setup detection during Windows release packaging.
- Improved detection of the Inno Setup command-line compiler.
- Improved Windows release packaging reliability.

---

## [3.7.1] - 2026-08-16

### Fixed

- Continued improvements to the Windows release and packaging process.
- Improved release build configuration.
- Improved compatibility between the PyInstaller application build and the Windows installer.

---

## [3.7.0] - 2026-08-16

### Added

- Added the Windows release packaging system.
- Added PyInstaller configuration for Windows application builds.
- Added Inno Setup configuration for Windows installers.
- Added GitHub Actions configuration for continuous integration and release workflows.
- Added repository screenshots.
- Added issue templates.
- Added a pull request template.
- Added contributing documentation.
- Added a security policy.
- Added a code of conduct.
- Added an original application icon for the application window, executable, and installer.

### Improved

- Polished the desktop interface.
- Improved the dark and light theme system.
- Added persistent theme preferences.
- Improved source configuration layout.
- Improved source configuration scrolling behavior.
- Prevented accidental mouse-wheel changes in source and theme selectors.
- Consolidated application status messaging.
- Improved the overall Windows desktop experience.

---

## Release Notes

### 3.7.3

The `3.7.3` release focuses primarily on making the Windows distribution process reliable.

The application can now be built locally with PyInstaller and packaged into a Windows installer using Inno Setup.

The resulting installer is:

```text
SouthParkDownloader-Setup-3.7.3.exe
```

### 3.7.2

The `3.7.2` release addressed problems locating Inno Setup during Windows release builds.

### 3.7.0

The `3.7.0` release established the current project structure, desktop interface improvements, Windows packaging infrastructure, repository documentation, and release tooling.

---

## Versioning

Versions use the following format:

```text
MAJOR.MINOR.PATCH
```

Git release tags use the `v` prefix:

```text
v3.7.3
```

For example:

```text
3.7.3
v3.7.3
```

should refer to the same release.

---

[3.7.3]: https://github.com/w0wzahh/southpark-downloader/releases/tag/v3.7.3
[3.7.2]: https://github.com/w0wzahh/southpark-downloader/releases/tag/v3.7.2
[3.7.1]: https://github.com/w0wzahh/southpark-downloader/releases/tag/v3.7.1
[3.7.0]: https://github.com/w0wzahh/southpark-downloader/releases/tag/v3.7.0