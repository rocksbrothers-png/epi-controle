class ContactLaunchResult {
  const ContactLaunchResult({
    required this.channel,
    required this.message,
    required this.launchUrl,
    required this.accessLink,
  });

  final String channel;
  final String message;
  final String launchUrl;
  final String accessLink;

  factory ContactLaunchResult.fromJson(Map<String, dynamic> json) =>
      ContactLaunchResult(
        channel: json['channel'] as String? ?? '',
        message: json['message'] as String? ?? '',
        launchUrl: json['launch_url'] as String? ?? '',
        accessLink: json['access_link'] as String? ?? '',
      );
}
