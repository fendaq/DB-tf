import tensorflow as tf
from db_config import cfg

def dice_coefficient_loss(y_true_cls, y_pred_cls,
                     training_mask):
    '''
    dice loss
    :param y_true_cls:
    :param y_pred_cls:
    :param training_mask:
    :return:
    '''
    eps = 1e-5
    intersection = tf.reduce_sum(y_true_cls * y_pred_cls * training_mask)
    union = tf.reduce_sum(y_true_cls * training_mask) + tf.reduce_sum(y_pred_cls * training_mask) + eps
    loss = 1. - (2 * intersection / union)
    tf.summary.scalar('classification_dice_loss', loss)
    return loss

def balance_cross_entropy_loss(gt, pred, mask,
                               negative_ratio=3.0, eps=1e-6):
    positive = gt * mask
    negative = (1 - gt) * mask
    positive_count = tf.reduce_sum(positive)
    negative_count = tf.minimum(tf.reduce_sum(negative), tf.int32(positive_count * negative_ratio))
    gt = tf.reshape(gt, [-1, 1])
    pred = tf.reshape(pred, [-1, 1])
    cross_entropy = tf.nn.sigmoid_cross_entropy_with_logits(labels=gt, logits=pred)
    positive_loss = cross_entropy * positive
    negative_loss = cross_entropy * negative
    negative_loss, _ = tf.nn.top_k(tf.reshape(negative_loss, -1), negative_count)

    balance_loss = (tf.reduce_sum(positive_loss) + tf.reduce_sum(negative_loss)) / (positive_count + negative_count + eps)

    return balance_loss

def softmax_cross_entropy_loss(y_true_cls, y_pred_cls, training_mask):
    '''
    softmax_cross_entropy(SCE) loss
    :param y_true_cls:[bs,w,h,N]
    :param y_pred_cls:[bs,w,h,N]
    :param training_mask:
    :return:
    '''
    re_mask = 1 - training_mask
    zero_mask = tf.zeros(tf.shape(re_mask))
    add_mask = tf.concat((re_mask, zero_mask, zero_mask), axis=3)

    y_true_cls = y_true_cls * training_mask + add_mask
    y_pred_cls = y_pred_cls * training_mask + add_mask

    y_true_cls = tf.reshape(y_true_cls, [-1, tf.shape(y_true_cls)[-1]])
    y_pred_cls = tf.reshape(y_pred_cls, [-1, tf.shape(y_true_cls)[-1]])

    cross_entropy = tf.nn.softmax_cross_entropy_with_logits(labels=y_true_cls, logits=y_pred_cls)
    cls_loss = tf.reduce_mean(cross_entropy)

    return cls_loss


def smooth_l1_loss(pred, gt, mask, sigma=1.0):
    '''

    :param bbox_pred:
    :param bbox_targets: shape is same as bbox_pred
    :param sigma:
    :return:
    '''
    sigma_2 = sigma**2

    diff = pred * mask - gt

    abs_diff = tf.abs(diff)

    smoothL1_sign = tf.stop_gradient(
        tf.to_float(tf.less(abs_diff, 1. / sigma_2)))
    loss = tf.pow(diff, 2) * (sigma_2 / 2.0) * smoothL1_sign \
               + (abs_diff - (0.5 / sigma_2)) * (1.0 - smoothL1_sign)
    return loss

def compute_loss(binarize_map, threshold_map, thresh_binary,
                 gt_score_maps, gt_threshold_map, gt_score_mask, gt_thresh_mask):

    binarize_loss = balance_cross_entropy_loss(gt_score_maps, binarize_map, gt_score_mask)
    threshold_loss = smooth_l1_loss(threshold_map, gt_threshold_map, gt_thresh_mask)
    thresh_binary_loss = dice_coefficient_loss(gt_score_maps, thresh_binary, gt_score_mask)

    model_loss = cfg.TRAIN.LOSS_ALPHA * binarize_loss + cfg.TRAIN.LOSS_BETA * threshold_loss + thresh_binary_loss

    return model_loss



