using Microsoft.Band;
using Microsoft.Band.Sensors;
using System;
using System.Linq; // Added for Min()
using System.Threading.Tasks;
using Windows.UI.Core;
using Windows.UI.Xaml;
using Windows.UI.Xaml.Controls;
using Windows.UI.Xaml.Navigation;
using System.Diagnostics; // For Debug.WriteLine

namespace App3
{
    public sealed partial class MainPage : Page
    {
        private IBandClient bandClient;
        private IBandInfo[] pairedBands;

        public MainPage()
        {
            this.InitializeComponent();
            Loaded += MainPage_Loaded;
        }

        private async void MainPage_Loaded(object sender, RoutedEventArgs e)
        {
            try
            {
                // Get paired Bands
                pairedBands = await BandClientManager.Instance.GetBandsAsync();
                if (pairedBands.Length == 0)
                {
                    StatusText.Text = "No Band paired. Pair via Bluetooth settings.";
                    return;
                }

                // Connect to the first Band
                bandClient = await BandClientManager.Instance.ConnectAsync(pairedBands[0]);
                StatusText.Text = "Connected to Band!";

                // Start reading sensors (GSR and Heart Rate)
                await StartSensorReadingsAsync();
            }
            catch (Exception ex)
            {
                StatusText.Text = $"Error: {ex.Message}";
            }
        }

        private async Task StartSensorReadingsAsync()
        {
            // GSR Sensor (Band 2 only)
            var gsrSensor = bandClient.SensorManager.Gsr;

            // Get and display supported intervals for GSR
            var gsrSupportedIntervals = gsrSensor.SupportedReportingIntervals;
            if (gsrSupportedIntervals != null && gsrSupportedIntervals.Any())
            {
                var minGsrInterval = gsrSupportedIntervals.Min();
                try
                {
                    gsrSensor.ReportingInterval = minGsrInterval;
                    StatusText.Text += $"\nGSR interval set to {minGsrInterval.TotalMilliseconds} ms (highest frequency).";
                }
                catch (Exception ex)
                {
                    StatusText.Text += $"\nFailed to set GSR interval: {ex.Message}. Using default.";
                }
            }
            else
            {
                StatusText.Text += "\nGSR does not support custom intervals. Using default (~5s).";
            }

            gsrSensor.ReadingChanged += async (s, args) =>
            {
                try
                {
                    await Dispatcher.RunAsync(CoreDispatcherPriority.Normal, () =>
                    {
                        // Update with latest GSR reading only
                        GSRDisplay.Text = $"Latest GSR Resistance: {args.SensorReading.Resistance} kOhms";
                    });

                    // Log to debug output
                    Debug.WriteLine($"GSR Resistance: {args.SensorReading.Resistance} kOhms");
                }
                catch (Exception ex)
                {
                    Debug.WriteLine($"GSR Handler Error: {ex.Message}");
                }
            };

            await gsrSensor.StartReadingsAsync();

            // Heart Rate Sensor (requires consent)
            var hrSensor = bandClient.SensorManager.HeartRate;

            // Request user consent if not already granted
            if (hrSensor.GetCurrentUserConsent() != UserConsent.Granted)
            {
                bool consented = await hrSensor.RequestUserConsentAsync();
                if (!consented)
                {
                    StatusText.Text += "\nHeart Rate consent denied. GSR only.";
                    return; // Or continue without HR
                }
            }

            // Get and display supported intervals for HR (optional, as it's already ~1s by default)
            var hrSupportedIntervals = hrSensor.SupportedReportingIntervals;
            if (hrSupportedIntervals != null && hrSupportedIntervals.Any())
            {
                var minHrInterval = hrSupportedIntervals.Min();
                try
                {
                    hrSensor.ReportingInterval = minHrInterval;
                    StatusText.Text += $"\nHR interval set to {minHrInterval.TotalMilliseconds} ms.";
                }
                catch (Exception ex)
                {
                    StatusText.Text += $"\nFailed to set HR interval: {ex.Message}. Using default.";
                }
            }

            hrSensor.ReadingChanged += async (s, args) =>
            {
                try
                {
                    await Dispatcher.RunAsync(CoreDispatcherPriority.Normal, () =>
                    {
                        // Update with latest HR reading only
                        HRDisplay.Text = $"Latest Heart Rate: {args.SensorReading.HeartRate} bpm (Quality: {args.SensorReading.Quality})";
                    });

                    // Log to debug output
                    Debug.WriteLine($"Heart Rate: {args.SensorReading.HeartRate} bpm (Quality: {args.SensorReading.Quality})");
                }
                catch (Exception ex)
                {
                    Debug.WriteLine($"HR Handler Error: {ex.Message}");
                }
            };

            await hrSensor.StartReadingsAsync();

            StatusText.Text += "\nGSR and Heart Rate sensors started!";
        }

        // Optional: Stop readings when navigating away
        protected override async void OnNavigatedFrom(NavigationEventArgs e)
        {
            if (bandClient != null)
            {
                await bandClient.SensorManager.Gsr.StopReadingsAsync();
                await bandClient.SensorManager.HeartRate.StopReadingsAsync();
                bandClient.Dispose();
            }
            base.OnNavigatedFrom(e);
        }
    }
}