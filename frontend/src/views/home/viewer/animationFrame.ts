export class AnimationFrame {
  private readonly callback: () => void;
  private frame = 0;
  private disposed = false;

  constructor(callback: () => void) {
    this.callback = callback;
  }

  request() {
    if (this.disposed || this.frame) {
      return;
    }

    this.frame = requestAnimationFrame(() => {
      this.frame = 0;
      this.callback();
    });
  }

  cancel() {
    cancelAnimationFrame(this.frame);
    this.frame = 0;
  }

  dispose() {
    this.cancel();
    this.disposed = true;
  }
}
