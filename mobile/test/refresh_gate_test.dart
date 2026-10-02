import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:safishacon_mobile/ui/widgets/common.dart';

void main() {
  test('a refresh requested mid-flight is queued, not dropped', () async {
    final gate = RefreshGate();
    final releases = <Completer<void>>[];
    var fetches = 0;
    Future<void> fetch() {
      fetches++;
      final done = Completer<void>();
      releases.add(done);
      return done.future;
    }

    // Background poll starts a fetch...
    final poll = gate.run(fetch);
    // ...then the customer submits a review and asks for fresh data twice.
    var afterReviewDone = false;
    final afterReview = gate.run(fetch).then((_) => afterReviewDone = true);
    gate.run(fetch);

    releases[0].complete(); // the stale (pre-review) response arrives
    await Future<void>.delayed(Duration.zero);
    expect(fetches, 2, reason: 'one extra fetch for all queued requests');
    expect(afterReviewDone, isFalse, reason: 'must wait for post-review data');

    releases[1].complete();
    await Future.wait([poll, afterReview]);
    expect(afterReviewDone, isTrue);
    expect(fetches, 2);
  });

  test('sequential refreshes each fetch once', () async {
    final gate = RefreshGate();
    var fetches = 0;
    await gate.run(() async => fetches++);
    await gate.run(() async => fetches++);
    expect(fetches, 2);
  });
}
