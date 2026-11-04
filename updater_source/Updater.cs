using System;
using System.Diagnostics;
using System.IO;
using System.Threading;

namespace RemoteWebMonitor
{
    class Updater
    {
        [STAThread]
        static void Main(string[] args)
        {
            // Penggunaan: Updater.exe <PID_PROSES_LAMA> <PATH_FILE_BARU> <PATH_FILE_TARGET> [ARGUMEN_TAMBAHAN]
            if (args.Length < 3)
            {
                return;
            }

            try
            {
                // 1. Bersihkan variabel lingkungan PyInstaller warisan dari memori saat ini
                Environment.SetEnvironmentVariable("_MEIPASS2", null);
                Environment.SetEnvironmentVariable("_MEIPASS", null);
                Environment.SetEnvironmentVariable("PYTHONHOME", null);
                Environment.SetEnvironmentVariable("PYTHONPATH", null);

                int oldPid;
                int.TryParse(args[0], out oldPid);
                string newFile = args[1];
                string targetFile = args[2];
                string extraArgs = args.Length > 3 ? args[3] : "";

                // 2. Tunggu proses aplikasi lama benar-benar mati dan melepaskan file lock
                if (oldPid > 0)
                {
                    try
                    {
                        Process proc = Process.GetProcessById(oldPid);
                        if (!proc.HasExited)
                        {
                            if (!proc.WaitForExit(4000))
                            {
                                proc.Kill();
                                proc.WaitForExit(1000);
                            }
                        }
                    }
                    catch
                    {
                        // Proses mungkin sudah keluar
                    }
                }

                // Beri jeda ekstra agar Windows OS melepaskan handle DLL/file sepenuhnya
                Thread.Sleep(800);

                // 3. Loop menyalin file baru menimpa file lama (hingga 10 kali retry)
                bool success = false;
                for (int i = 0; i < 10; i++)
                {
                    try
                    {
                        if (File.Exists(newFile))
                        {
                            File.Copy(newFile, targetFile, true);
                            success = true;
                            break;
                        }
                    }
                    catch
                    {
                        Thread.Sleep(800);
                    }
                }

                // 4. Hapus file unduhan sementara setelah berhasil disalin
                if (success)
                {
                    try
                    {
                        if (File.Exists(newFile))
                        {
                            File.Delete(newFile);
                        }
                    }
                    catch { }

                    // 5. Jalankan aplikasi baru
                    // Jika ada argumen tambahan (seperti --minimized untuk ClientAgent)
                    if (!string.IsNullOrEmpty(extraArgs))
                    {
                        ProcessStartInfo psi = new ProcessStartInfo();
                        psi.FileName = targetFile;
                        psi.Arguments = extraArgs;
                        psi.WorkingDirectory = Path.GetDirectoryName(targetFile);
                        psi.UseShellExecute = true;
                        Process.Start(psi);
                    }
                    else
                    {
                        // Untuk ServerAdmin: Luncurkan via explorer.exe Windows Shell murni
                        // Ini menjamin 100% proses baru di-spawn dari Desktop tanpa mewarisi memory leak apapun!
                        ProcessStartInfo psi = new ProcessStartInfo();
                        psi.FileName = "explorer.exe";
                        psi.Arguments = "\"" + targetFile + "\"";
                        psi.UseShellExecute = false;
                        Process.Start(psi);
                    }
                }
            }
            catch { }
        }
    }
}
