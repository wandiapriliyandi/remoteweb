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
            // Argumen: Updater.exe <PID_PROSES_LAMA> <PATH_FILE_BARU> <PATH_FILE_TARGET> [ARGUMEN_TAMBAHAN]
            if (args.Length < 3)
            {
                return;
            }

            try
            {
                int oldPid;
                int.TryParse(args[0], out oldPid);
                string newFile = args[1];
                string targetFile = args[2];
                string extraArgs = args.Length > 3 ? args[3] : "";

                // 1. Tunggu proses aplikasi lama benar-benar mati dan melepaskan file lock
                if (oldPid > 0)
                {
                    try
                    {
                        Process proc = Process.GetProcessById(oldPid);
                        if (!proc.HasExited)
                        {
                            if (!proc.WaitForExit(5000))
                            {
                                proc.Kill();
                                proc.WaitForExit(1000);
                            }
                        }
                    }
                    catch
                    {
                        // Proses mungkin sudah keluar sebelum ini
                    }
                }

                // Beri jeda ekstra agar Windows OS melepaskan handle DLL/file sepenuhnya
                Thread.Sleep(1000);

                // 2. Loop menyalin file baru menimpa file lama (hingga 10 kali retry jika file masih terkunci)
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
                        Thread.Sleep(1000);
                    }
                }

                // 3. Hapus file unduhan sementara setelah berhasil disalin
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

                    // 4. Jalankan aplikasi baru melalui Windows Shell independen (bersih dari memori lama)
                    string workDir = Path.GetDirectoryName(targetFile);
                    ProcessStartInfo psi = new ProcessStartInfo();
                    psi.FileName = targetFile;
                    psi.WorkingDirectory = workDir;
                    if (!string.IsNullOrEmpty(extraArgs))
                    {
                        psi.Arguments = extraArgs;
                    }
                    psi.UseShellExecute = true;
                    Process.Start(psi);
                }
            }
            catch { }
        }
    }
}
