import 'package:flutter/material.dart';

import '../theme.dart';

/// Replace curated local photographs here without changing screen layouts.
abstract final class EditorialImages {
  static const home = 'assets/images/home/dar-living-room.webp';
  static const brightHome = 'assets/images/onboarding/nairobi-apartment.webp';
  static const peacefulHome = home;
  static const workspace = 'assets/images/services/dar-workspace.webp';
  static const services = {
    'general-home-cleaning': home,
    'deep-cleaning': brightHome,
    'office-cleaning': workspace,
    'move-in-move-out': brightHome,
    'sofa-carpet-cleaning': home,
  };

  static ImageProvider provider(String asset, {int width = 960}) =>
      ResizeImage(AssetImage(asset), width: width);
}

class EditorialPhoto extends StatelessWidget {
  final String asset;
  final String label;
  final double height;
  final Alignment alignment;
  final int decodeWidth;
  const EditorialPhoto({
    super.key,
    required this.asset,
    required this.label,
    required this.height,
    this.alignment = Alignment.center,
    this.decodeWidth = 960,
  });

  @override
  Widget build(BuildContext context) => ColoredBox(
    color: Brand.green50,
    child: Image(
      image: EditorialImages.provider(asset, width: decodeWidth),
      height: height,
      width: double.infinity,
      fit: BoxFit.cover,
      alignment: alignment,
      semanticLabel: label,
      errorBuilder: (_, _, _) => SizedBox(
        height: height,
        child: const Center(
          child: Icon(Icons.home_outlined, size: 48, color: Brand.green700),
        ),
      ),
    ),
  );
}
